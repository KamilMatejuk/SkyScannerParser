import os
import time
import shutil
import argparse
import itertools
import webbrowser
import pandas as pd

from skyscanner import build_url, parse_page
from logger import get_logger

logger = get_logger(__name__)


def main(args):
    links = []
    for start, end, date in itertools.product(args.start, args.end, args.date):
        if start == end: continue
        link = build_url(
            start=start,
            end=end,
            departure_date=date,
            max_duration=args.max_duration,
            stop=args.stop
        )
        links.append((start, end, date, link))
    
    if os.path.exists(args.output):
        data = pd.read_csv(args.output)
        data['departure'] = pd.to_datetime(data['departure'])
        data['arrival'] = pd.to_datetime(data['arrival'])
    else: data = pd.DataFrame()

    for i, (start, end, date, link) in enumerate(links):
        logger.warning(f"[{i+1}/{len(links)}] Downloading {start} -> {end} on {date}")
        # check if already downloaded in df
        exists = not data.empty and data[
            (data['start'] == start) &
            (data['end'] == end) &
            (data['departure'].dt.strftime("%d.%m.%Y") == date)
        ].shape[0] > 0
        if exists:
            logger.debug(f"Skipping, already in {args.output}")
            continue
        # open in chrome
        webbrowser.open(link)
        # watch changes in downloads
        filename = None
        while True:
            files = [f for f in os.listdir(args.folder) if f.endswith(".html")]
            if not files:
                logger.debug("Waiting for download...")
                time.sleep(3)
                continue
            filename = files[0]
            logger.debug(f"Detected downloaded file: {filename}")
            break
        # load saved html and parse
        with open(os.path.join(args.folder, filename), "r", encoding="utf-8") as f:
            html = f.read()
        df = parse_page(html)
        logger.debug(f"Parsed {len(df)} flights")
        # save to db
        data = pd.concat([data, df], ignore_index=True) if not data.empty else df
        data.to_csv(args.output, index=False)
        logger.debug(f"Saved to {args.output}")
        os.remove(os.path.join(args.folder, filename))
        shutil.rmtree(os.path.join(args.folder, filename.replace(".html", "_files")))
        logger.debug(f"Removed downloaded files.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Skyscanner pages")
    # filters
    parser.add_argument("-s", "--start", action="append", required=True, help="Start city names")
    parser.add_argument("-e", "--end", action="append", required=True, help="End city names")
    parser.add_argument("-d", "--date", action="append", required=True, help="Departure dates in DD.MM.YYYY format")
    parser.add_argument("--open", type=int, default=5, help="How many links to open at one time in the browser (default: 5)")
    parser.add_argument("--max_duration", type=int, default=600, help="Maximum flight duration in minutes")
    parser.add_argument("--stop", action="store_true", help="Allow stops in the flight")
    # download
    parser.add_argument("-f", "--folder", default=f"{os.environ['HOME']}/Downloads", help="Folder containing HTML files")
    parser.add_argument("-o", "--output", default="flights_parsed.csv", help="Output CSV file name")
    
    args = parser.parse_args()
    main(args)
