import datetime
import pandas as pd
from bs4 import BeautifulSoup

from utils import get_airport_city


AIRPORT = {
    # poland
    "Gdańsk": "gada",
    "Katowice": "kato",
    "Kraków": "krak",
    "Poznań": "pozn",
    "Warszawa": "wars",
    "Wrocław": "wroc",
    # malta
    "Valletta": "mlaa",
}

PL_MONTHS = {
    "sty": 1,  # styczeń
    "lut": 2,  # luty
    "mar": 3,  # marzec
    "kwi": 4,  # kwiecień
    "maj": 5,  # maj
    "cze": 6,  # czerwiec
    "lip": 7,  # lipiec
    "sie": 8,  # sierpień
    "wrz": 9,  # wrzesień
    "paź": 10, # październik
    "lis": 11, # listopad
    "gru": 12, # grudzień
}


def build_url(start: str, end: str, departure_date: str, max_duration: int, stop: bool) -> str:
    date_slug = datetime.datetime.strptime(departure_date, "%d.%m.%Y").strftime("%y%m%d")
    base = "https://www.skyscanner.pl/transport/loty"
    query = (
        "?adultsv2=1&cabinclass=economy&childrenv2=&ref=home&rtn=0"
        "&outboundaltsenabled=false&inboundaltsenabled=false"
    )
    query += f"&duration={max_duration}" # in minutes
    query += f"&stops={'!twoPlusStops' if stop else '!oneStop,!twoPlusStops'}"
    return f"{base}/{AIRPORT[start]}/{AIRPORT[end]}/{date_slug}/{query}"


def parse_page(html: str) -> pd.DataFrame:
    soup = BeautifulSoup(html, "html.parser")
    start = soup.select_one('[class*="SearchDetails_search__origin__"]').text.split("(")[0].strip()
    end = soup.select_one('[class*="SearchDetails_search__destination__"]').text.split("(")[0].strip()
    day = soup.select_one('[class*="MiniGrid_cellSelected__"] > span').text.strip()
    day_part, month_abbr = day.strip().split()
    date = datetime.datetime(datetime.datetime.now().year, PL_MONTHS[month_abbr.lower()], int(day_part)).date()
    results = soup.select_one('[class*="FlightsResults_dayViewItems__"]')
    ticket_containers = results.select('[class*="FlightsTicket_container__"]')
    results = []
    for ticket_container in ticket_containers:
        link = ticket_container.select_one('a')['href']
        airline = ticket_container.select_one('[class*="LogoImage_label__"]').text.strip()
        departure_time = ticket_container.select_one('[class*="RoutePartial_routePartialDepart__"] > span').text.strip()
        departure = datetime.datetime.combine(date, datetime.datetime.strptime(departure_time, "%H:%M").time())
        arrival_time = ticket_container.select_one('[class*="RoutePartial_routePartialArrive__"] > span').text.strip()
        arrival = datetime.datetime.combine(date, datetime.datetime.strptime(arrival_time, "%H:%M").time())
        stops = ticket_container.select_one('[class*="Stops_stopsLabelContainer__"]').text.strip()
        if "Bezpośredni" in stops: stops = None
        else: stops = get_airport_city(stops.replace(u'\xa0', u' ').split(" ")[-1].strip())
        price = ticket_container.select_one('[class*="Price_mainPriceContainer__"]').text.strip()
        price = float("".join(price.replace(u'\xa0', u' ').split(" ")[:-1]))
        results.append({
            "start": start,
            "end": end,
            "link": link,
            "airline": airline,
            "departure": departure,
            "arrival": arrival,
            "duration": arrival - departure,
            "stops": stops,
            "price": price,
        })
    results = pd.DataFrame(results)
    return results
