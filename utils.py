import pandas as pd


def get_airport_city(code: str) -> str:
    df = pd.read_csv("airport-codes.csv")
    city = df.loc[df['iata_code'] == code.upper(), 'municipality'].iloc[0]
    country = df.loc[df['iata_code'] == code.upper(), 'iso_country'].iloc[0]
    return f"{city}, {country}"
