import os
import calendar
import datetime
import pandas as pd
import streamlit as st



# --- Session state defaults -------------------------------------------------

def set_session(key, default):
    if key not in st.session_state:
        st.session_state[key] = default
set_session('uploaded', False)
set_session('filename', '')
set_session('flights_df', None)
set_session('pairs_df', None)
set_session('selection_shown', False)

# --- Helpers ----------------------------------------------------------------

@st.cache_data
def read_csv(filename: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(filename)
        df['departure'] = pd.to_datetime(df['departure'])
        df['arrival'] = pd.to_datetime(df['arrival'])
        df['duration'] = pd.to_timedelta(df['duration'])
        return df
    except Exception as e:
        st.error(f"Failed to read file: {e}")

@st.cache_data
def generate_pairs(flights_df: pd.DataFrame,
                   start_cities: list[str],
                   end_cities: list[str],
                   holidays: list[datetime.date],
                   workday_hours: tuple[int, int],
                   baggage_price: int,
                   night_price: int,
                   eat_price: int,
                   max_nights: int) -> pd.DataFrame:
    pairs = []
    # remove outside workday hours
    flights_df = flights_df[
        (flights_df['departure'].dt.date.isin(holidays)) | 
        (
            (flights_df['departure'].dt.hour >= workday_hours[0]) &
            (flights_df['departure'].dt.hour <= workday_hours[1])
        )]
    # find in and outbound flights
    outbound_flights = flights_df[flights_df['start'].isin(start_cities) & flights_df['end'].isin(end_cities)]
    inbound_flights = flights_df[flights_df['start'].isin(end_cities) & flights_df['end'].isin(start_cities)]
    # join
    for _, outbound in outbound_flights.iterrows():
        for _, inbound in inbound_flights.iterrows():
            if inbound['departure'] <= outbound['arrival']: continue
            nights = (inbound['departure'].date() - outbound['departure'].date()).days
            if nights > max_nights: continue
            free_days = sum(outbound['arrival'].date() < d < inbound['departure'].date() for d in holidays)
            if outbound['arrival'].date() in holidays and outbound['arrival'].hour < 15: free_days += 1
            if inbound['departure'].date() in holidays and inbound['departure'].hour >= 15: free_days += 1
            pairs.append({
                'out_price': outbound['price'],
                'out_airport': format_airport(outbound),
                'out_date': format_date(outbound),
                'out_time': format_time(outbound),
                'nights': nights,
                'free_days': free_days,
                'in_price': inbound['price'],
                'in_airport': format_airport(inbound),
                'in_date': format_date(inbound),
                'in_time': format_time(inbound),
                'flight_price': outbound['price'] + inbound['price'],
                'baggage_price': baggage_price * (2 + (0 if pd.isna(inbound['stops']) else 1) + (0 if pd.isna(outbound['stops']) else 1)),
                'live_price': night_price * nights + eat_price * (nights + 1),
                'total_price': outbound['price'] + inbound['price'] + 
                               night_price * nights + 
                               eat_price * (nights + 1) + 
                               baggage_price * (2 + (0 if pd.isna(inbound['stops']) else 1) + (0 if pd.isna(outbound['stops']) else 1)),
                'out_link': outbound['link'],
                'in_link': inbound['link'],
            })
    return pd.DataFrame(pairs)

def format_airport(data: pd.Series) -> str:
    if pd.isna(data['stops']):
        return f"{data['start']} -> {data['end']}"
    return f"{data['start']} -> {data['stops']} -> {data['end']}"

def format_date(data: pd.Series) -> str:
    return data['departure'].strftime('%a %d.%m.%Y')

def format_time(data: pd.Series) -> str:
    start = data['departure'].strftime('%H:%M')
    end = data['arrival'].strftime('%H:%M')
    duration = data['duration']
    h, s = divmod(duration.seconds, 3600)
    m = s // 60
    return f"{start}-{end} ({h}h {m}m)"

def filter_slider(pairs: pd.DataFrame, keys: list[str], label: str | None = None) -> pd.DataFrame:
    min_value = min(pairs[key].min() for key in keys)
    max_value = max(pairs[key].max() for key in keys)
    if min_value == max_value: return pairs
    value = st.slider(f'Select {label or " ".join(keys)} range', min_value=min_value, max_value=max_value, value=(min_value, max_value))
    filtered = pairs
    for key in keys:
        filtered = filtered[(filtered[key] >= value[0]) & (filtered[key] <= value[1])]
    return filtered

# --- Layout ------------------------------------------------------------------

def main_file_upload():
    st.info('Upload a CSV file with flights to begin')
    uploaded = st.file_uploader('Upload CSV', type=['csv'], accept_multiple_files=False)
    if uploaded is not None:
        try:
            flights_df = read_csv(uploaded)
            st.session_state['flights_df'] = flights_df
            st.session_state['filename'] = uploaded.name.replace('.csv', '')
            st.session_state['uploaded'] = True
            st.rerun()
        except Exception as e:
            st.error(f'Failed to read CSV: {e}')
            st.stop()

def main_start_end_selection():
    flights_df: pd.DataFrame = st.session_state['flights_df']
    st.success(f'Flights loaded — rows: {len(flights_df)} columns: {len(flights_df.columns)}')
    c1, c2 = st.columns([1, 1])
    # start and end cities
    cities = set(flights_df['start'].dropna().unique().tolist() + flights_df['end'].dropna().unique().tolist())
    with c1:
        start_selection = st.multiselect('Start cities', options=cities)
        end_selection = st.multiselect('End cities', options=cities)
        st.write('Additional price estimation')
        c11, c12, c13 = st.columns([1, 1, 1])
        with c11:
            baggage_price = st.number_input('Luggage (per flight, PLN)', min_value=0, step=10, value=0)
        with c12:
            night_price = st.number_input('Sleep (per night, PLN)', min_value=0, step=10, value=0)
        with c13:
            eat_price = st.number_input('Eat (per day, PLN)', min_value=0, step=10, value=0)
    # holidays
    days = sorted(set(flights_df['departure'].dt.date.unique().tolist() + flights_df['arrival'].dt.date.unique().tolist()))
    with c2:
        holidays = st.multiselect(
            'Holidays',
            options=days,
            default=[d for d in days if d.weekday() in (5, 6)],
            format_func=lambda d: f"{d} ({calendar.day_abbr[d.weekday()]})")
        workday_hours = st.slider('Workday hours', min_value=0, max_value=24, value=(0, 24))
        max_days = (flights_df['arrival'].max().date() - flights_df['departure'].min().date()).days
        max_nights = st.slider('Max nights', min_value=0, max_value=max_days, value=min(max_days, 10))
    # run
    show_btn = len(start_selection) > 0 and len(end_selection) > 0
    if st.button('Generate round trips', disabled=not show_btn, width='stretch'):
        pairs = generate_pairs(flights_df,
                               start_selection, end_selection,
                               holidays, workday_hours,
                               baggage_price, night_price, eat_price,
                               max_nights)
        st.session_state['pairs_df'] = pairs
        st.session_state['selection_shown'] = True
        st.rerun()

def main_results():
    pairs: pd.DataFrame = st.session_state['pairs_df']
    side, main = st.columns([1, 3], gap='medium')
    with side:
        st.write('### Filters')
        filtered = filter_slider(pairs, ['nights'])
        filtered = filter_slider(filtered, ['in_price', 'out_price'], 'price per flight')
        filtered = filter_slider(filtered, ['total_price'], 'total price')
        filtered = filter_slider(filtered, ['free_days'], 'free days')
        if st.checkbox('Only direct flights', value=False):
            filtered = filtered[
                (filtered['out_airport'].str.count('->') == 1) &
                (filtered['in_airport'].str.count('->') == 1)]
        if st.checkbox('Only same origin city', value=False):
            filtered = filtered[
                filtered['out_airport'].str.split(' -> ').str[0] ==
                filtered['in_airport'].str.split(' -> ').str[-1]]
        if st.checkbox('Only same target city', value=False):
            filtered = filtered[
                filtered['out_airport'].str.split(' -> ').str[-1] ==
                filtered['in_airport'].str.split(' -> ').str[0]]
    with main:
        if filtered is None or len(filtered) == 0:
            st.warning('No rows matched the selection — click Reset to try again.')
        else:
            st.write(f'### Generated roundtrip flights: {len(filtered)}')
            show = filtered.drop(columns=['out_price', 'in_price'], axis=1)
            show = show.sort_values(by=['total_price', 'free_days', 'nights'], ascending=[True, False, True])
            # apply favourites
            show = show.assign(favourite=False)
            show = show[['favourite'] + [c for c in show.columns if c != 'favourite']]
            try:
                favourite = pd.read_csv(st.session_state['filename'] + '_fav.csv')
                keys = ['out_link', 'in_link']
                show['favourite'] = show[keys].apply(tuple, axis=1).isin(favourite[keys].apply(tuple, axis=1))
            except FileNotFoundError: pass
            # show df
            columns = {
                "out_link": st.column_config.LinkColumn("out_link"),
                "in_link": st.column_config.LinkColumn("in_link"),
                "favourite": st.column_config.CheckboxColumn("⭐"),
            }
            edited = st.data_editor(show, hide_index=True, height=700, column_config=columns,
                key="editor", disabled=[c for c in show.columns if c != "favourite"])
            # handle favourites change
            favourite = edited[edited["favourite"]]
            if len(favourite) > 0 or os.path.exists(st.session_state['filename'] + '_fav.csv'):
                favourite.to_csv(st.session_state['filename'] + '_fav.csv', index=False)


def main():
    st.set_page_config(page_title="DataFrame Explorer", layout="wide")
    if not st.session_state['uploaded']:
        main_file_upload()
    elif not st.session_state['selection_shown']:
        main_start_end_selection()
    else:
        main_results()


if __name__ == '__main__':
    main()
