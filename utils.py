import pandas as pd


def get_airport_city(code: str) -> str:
    df = pd.read_csv("airport-codes.csv")
    try:
        city = df.loc[df['iata_code'] == code.upper(), 'municipality'].iloc[0]
        country = df.loc[df['iata_code'] == code.upper(), 'iso_country'].iloc[0]
        return f"{city}, {country}"
    except IndexError:
        return f"Unknown {code.upper()}"
