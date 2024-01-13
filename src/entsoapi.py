import pandas as pd
from entsoe import EntsoePandasClient
from src.general_functions import check_previous_data
import os
import pytz
import streamlit as st

@st.cache_data(show_spinner=False, max_entries=200, persist=True)
def get_finnish_price_data(start, end, _daterange=None):
    old_df = pd.read_csv('./data/old_finnish_price_data.csv')
    old_df['Aikaleima'] = pd.to_datetime(old_df['Aikaleima'])
    old_df.set_index(['Aikaleima'], inplace=True)

    new_start_time = check_previous_data(old_df, start)
    if new_start_time.date() < end:
        token = os.environ['ENTSO_TOKEN']
        tz_pytz = pytz.timezone("Etc/GMT+3")
        client = EntsoePandasClient(api_key=token)
        if _daterange is None:
            start_ts = pd.to_datetime(new_start_time, utc=True).tz_convert('Etc/GMT+3')
            end_ts = pd.to_datetime(end, utc=True).tz_convert('Etc/GMT+3')
        else:
            start_ts = _daterange[0]
            end_ts = _daterange[-1]
        country_code = 'FI'
        df = client.query_day_ahead_prices(country_code, start=start_ts, end=end_ts)
        df.name = 'FI'
        df.index.name = ['Aikaleima', 'Hinta']
        df = pd.concat([old_df, df])
        df.to_csv('./data/old_finnish_price_data.csv')
    else:
        df = old_df
    start = pd.to_datetime(start).tz_localize('Europe/Helsinki')
    end = pd.to_datetime(end).tz_localize('Europe/Helsinki') + pd.to_timedelta(1, 'day')
    print(df.loc[start:end].round(1))
    return df.loc[start:end].round(1)

@st.cache_data(show_spinner=False, max_entries=200)
def get_area_price_data(start, end, area, _daterange=None):
    token = os.environ['ENTSO_TOKEN']
    tz_pytz = pytz.timezone("Etc/GMT+3")
    client = EntsoePandasClient(api_key=token)
    if _daterange == None:
        start_ts = pd.to_datetime(start, utc=True).tz_convert('Etc/GMT+3')
        end_ts = pd.to_datetime(end, utc=True).tz_convert('Etc/GMT+3')
    else:
        start_ts = _daterange[0]
        end_ts = _daterange[-1]
    df = client.query_day_ahead_prices(area, start=start_ts, end=end_ts)
    df.name = area
    return df
