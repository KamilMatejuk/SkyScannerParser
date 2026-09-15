import os
import re
import time
import shutil
import argparse
import pyautogui
import itertools
import traceback
import webbrowser
import datetime
import pandas as pd


from skyscanner import build_url, parse_page
from utils import MOUSE_POSITION
from logger import get_logger

logger = get_logger(__name__)



def _parse_single_date(date: str) -> datetime.date:
    if re.match(r"[0-9]{2}\.[0-9]{2}\.[0-9]{4}", date):
        return datetime.datetime.strptime(date, "%d.%m.%Y").date()
    raise ValueError(f"{date} is not date DD.MM.YYYY")

def _parse_double_date(date: str) -> list[datetime.date]:
    if m := re.match(r"([0-9]{2}\.[0-9]{2}\.[0-9]{4})-([0-9]{2}\.[0-9]{2}\.[0-9]{4})", date):
        start = datetime.datetime.strptime(m.group(1), "%d.%m.%Y").date()
        end = datetime.datetime.strptime(m.group(2), "%d.%m.%Y").date()
        return [start + datetime.timedelta(days=i) for i in range((end - start).days + 1)]
    raise ValueError(f"{date} is not range of dates DD.MM.YYYY-DD.MM.YYYY")


def parse_dates(dates: list[str], must_have_dates: str, range_dates: str) -> list[tuple[datetime.date, bool]]:
    # parse dates and ranges
    parsed_dates = []
    for date in dates:
        try: parsed_dates.append(_parse_single_date(date)); continue
        except ValueError: pass
        try: parsed_dates.extend(_parse_double_date(date)); continue
        except ValueError: pass
        raise ValueError(f"{date} is neither date DD.MM.YYYY nor range of dates DD.MM.YYYY-DD.MM.YYYY")
    dates = [(d, False) for d in parsed_dates]
    # validate auto expansion
    if not must_have_dates and not range_dates:
        return dates
    if not must_have_dates or not range_dates:
        raise ValueError("Both must-have-dates or range-dates must be provided.")
    mhd_start, *_, mhd_end = _parse_double_date(must_have_dates)
    _, max_days = map(int, range_dates.split("-"))
    # outbound
    out_start = mhd_start - datetime.timedelta(days=max_days - 2)
    out_end = mhd_end
    dates.extend([(out_start + datetime.timedelta(days=i), False) for i in range((out_end - out_start).days + 1)])
    # inbound
    in_start = mhd_start + datetime.timedelta(days=1)
    in_end = mhd_end + datetime.timedelta(days=max_days - 1)
    dates.extend([(in_start + datetime.timedelta(days=i), True) for i in range((in_end - in_start).days + 1)])
    return dates


def get_cases(args: argparse.Namespace) -> list[tuple[str, str, datetime.date, str]]:
    dates = parse_dates(args.date or [], args.must_have_dates, args.range_dates)
    cases = []
    for start, end, (date, is_return) in itertools.product(args.start, args.end, dates):
        if start == end: continue
        if is_return: start, end = end, start
        link = build_url(start=start, end=end, departure_date=date, max_duration=args.max_duration, stops=args.stops)
        cases.append((start, end, date, link))
    return cases


def main(args):
    if os.path.exists(args.output):
        data = pd.read_csv(args.output)
        data['departure'] = pd.to_datetime(data['departure'])
        data['arrival'] = pd.to_datetime(data['arrival'])
    else: data = pd.DataFrame()

    cases = get_cases(args)
    for i, (start, end, date, link) in enumerate(cases):
        try:
            logger.warning(f"[{i+1}/{len(cases)}] Downloading {start} -> {end} on {date}")
            # check if already downloaded in df
            exists = not data.empty and data[
                (data['start'] == start) &
                (data['end'] == end) &
                (data['departure'].dt.date == date)
            ].shape[0] > 0
            if exists:
                logger.debug(f"Skipping, already in {args.output}")
                continue
            # open in chrome
            webbrowser.open(link)
            # wait for load
            logger.debug("Waiting for page to load...")
            time.sleep(15)
            # save page using hotkeys
            logger.debug("Saving page...")
            pyautogui.hotkey("ctrl", "s")
            time.sleep(1)
            pyautogui.moveTo(*MOUSE_POSITION)
            pyautogui.click()
            # watch changes in downloads
            filename = None
            while True:
                files = [f for f in os.listdir(args.folder) if f.endswith(".html")]
                if not files:
                    logger.debug("Waiting for download...")
                    time.sleep(1)
                    continue
                filename = files[0]
                logger.debug(f"Detected downloaded file: {filename}")
                break
            # close tab
            pyautogui.hotkey("ctrl", "w")
            # load saved html and parse
            with open(os.path.join(args.folder, filename), "r", encoding="utf-8") as f:
                html = f.read()
            df = parse_page(html, start, end, date)
            logger.debug(f"Parsed {len(df)} flights")
            # save to db
            data = pd.concat([data, df], ignore_index=True) if not data.empty else df
            data.to_csv(args.output, index=False)
            logger.debug(f"Saved to {args.output}")
            os.remove(os.path.join(args.folder, filename))
            shutil.rmtree(os.path.join(args.folder, filename.replace(".html", "_files")))
            logger.debug(f"Removed downloaded files.")
        except Exception as e:
            logger.error(f"Error processing {start} -> {end} on {date}")
            logger.error(f"Link: {link}")
            for line in traceback.format_exc().splitlines():
                logger.error(line)
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Skyscanner pages")
    # params
    parser.add_argument("-s", "--start", action="append", nargs="+", required=True, help="Start city names")
    parser.add_argument("-e", "--end", action="append", nargs="+", required=True, help="End city names")
    parser.add_argument("-d", "--date", action="append", help="Departure date in DD.MM.YYYY or range DD.MM.YYYY-DD.MM.YYYY format")
    parser.add_argument("-md", "--must-have-dates", help="The must-have dates to be inclded in range DD.MM.YYYY-DD.MM.YYYY format")
    parser.add_argument("-rd", "--range-dates", help="The range of days of stay in N-N format")
    # filters
    parser.add_argument("--max_duration", type=int, default=600, help="Maximum flight duration in minutes")
    parser.add_argument("--stops", type=int, help="Max allowed stops in the flight")
    # download
    parser.add_argument("-f", "--folder", default=f"{os.environ['HOME']}/Downloads", help="Folder containing HTML files")
    parser.add_argument("-o", "--output", default="flights_parsed.csv", help="Output CSV file name")
    
    args = parser.parse_args()
    # flatten start and end lists
    args.start = list(itertools.chain.from_iterable(args.start))
    args.end = list(itertools.chain.from_iterable(args.end))

    main(args)
