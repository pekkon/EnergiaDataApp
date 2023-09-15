import pandas as pd
from entsoe import EntsoePandasClient
import os
import pytz
import streamlit as st

@st.cache_data(show_spinner=False, max_entries=200)
def get_price_data(start, end, _daterange):
    token = os.environ['ENTSO_TOKEN']
    tz_pytz = pytz.timezone("Etc/GMT+3")
    client = EntsoePandasClient(api_key=token)
    start_ts = _daterange[0]
    end_ts = _daterange[-1]
    country_code = 'FI'
    df = client.query_day_ahead_prices(country_code, start=start_ts, end=end_ts)
    return df
