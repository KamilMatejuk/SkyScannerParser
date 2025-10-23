import sys
import argparse
import itertools
import webbrowser

from skyscanner import build_url


def generate_links(start_cities, end_cities, departure_dates, max_duration, stop):
    links = []
    for start, end, date in itertools.product(start_cities, end_cities, departure_dates):
        if start == end:
            continue
        link = build_url(
            start=start,
            end=end,
            departure_date=date,
            max_duration=max_duration,
            stop=stop
        )
        links.append(link)
    return links


def open_links_in_browser(links, batch_size):
    for i in range(0, len(links), batch_size):
        print(f"Opening links {i + 1}-{min(i + batch_size, len(links))} out of {len(links)}")
        while True:
            cont = input("Press Enter to continue, or 'q' to quit: ")
            if cont == "": break
            elif cont.lower() == "q": sys.exit(0)
        for link in links[i:i+batch_size]:
            webbrowser.open(link)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get Skyscanner flight links.")
    parser.add_argument("-s", "--start", action="append", required=True, help="Start city names")
    parser.add_argument("-e", "--end", action="append", required=True, help="End city names")
    parser.add_argument("-d", "--date", action="append", required=True, help="Departure dates in DD.MM.YYYY format")
    parser.add_argument("--open", type=int, default=5, help="How many links to open at one time in the browser (default: 5)")
    parser.add_argument("--max_duration", type=int, default=600, help="Maximum flight duration in minutes")
    parser.add_argument("--stop", action="store_true", help="Allow stops in the flight")
    args = parser.parse_args()

    links = generate_links(
        start_cities=args.start,
        end_cities=args.end,
        departure_dates=args.date,
        max_duration=args.max_duration,
        stop=args.stop
    )
    open_links_in_browser(links, args.open)
