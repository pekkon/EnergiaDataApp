import plotly.subplots
import streamlit as st
from streamlit_extras.chart_container import chart_container
from streamlit_extras.toggle_switch import st_toggle_switch
import plotly.express as px
import pandas as pd
import numpy as np
from src.general_functions import get_general_layout, aggregate_data
from src.fmi_api import temperatures
from src.fingridapi import get_data_from_FG_API_with_start_end
import datetime



def get_wind_df(start, end):
    """
    Get the wind production and capacity values from Fingrid API between the start and end dates.
    Calculates the utilization rate
    :param start: start date
    :param end: end date
    :return: wind dataframe
    """
    wind_df = get_data_from_FG_API_with_start_end(75, start, end)
    wind_df.rename({'Value': 'Tuulituotanto'}, axis=1, inplace=True)

    wind_capacity = get_data_from_FG_API_with_start_end(268, start, end)
    # Fixing issues in the API capacity (sometimes capacity is missing and API gives low value)
    wind_capacity.loc[wind_capacity['Value'] < wind_capacity['Value'].shift(-24), 'Value'] = np.NaN
    wind_capacity['Value'] = wind_capacity['Value'].ffill()
    wind_df['Kapasiteetti'] = wind_capacity['Value']
    wind_df['Käyttöaste'] = wind_df['Tuulituotanto'] / wind_df['Kapasiteetti'] * 100

    return wind_df.round(1)


@st.cache_data(show_spinner=False, max_entries=200)
def get_temperatures(start_time, end_time):
    old_df = pd.read_csv('./old_temperatures.csv')
    old_df['Aikaleima'] = pd.to_datetime(old_df['Aikaleima'])
    old_df.set_index(['Aikaleima'], inplace=True)

    df = temperatures(start_time, end_time)
    temperature_df = pd.concat([old_df, df])
    wind_df = get_wind_df(datetime.date(2018, 1, 1), end_date)
    temperature_df['Keskilämpötila'] = temperature_df.mean(axis=1)
    filtered_temp_df = temperature_df.loc[start_date:end_date].iloc[:-1]
    filtered_wind_df = wind_df.loc[start_date:end_date].iloc[:-1]
    filtered_df = pd.merge_asof(filtered_temp_df, filtered_wind_df, left_index=True, right_index=True)
    filtered_df = aggregate_data(filtered_df, aggregation_selection)
    filtered_df['Vuosi'] = filtered_df.index.year.astype(str)
    return filtered_df

st.set_page_config(
    page_title="EnergiaData - Tuuli- ja sähköjärjestelmätilastoja",
    page_icon="https://i.imgur.com/Kd4P3y2.png",
    layout='wide',
    initial_sidebar_state='expanded'
)

old_start_dt= datetime.datetime(2018, 1, 1, 0, 0, 0)
old_end_dt = datetime.datetime(2023, 4, 23, 23, 59, 0)
new_start_dt= datetime.datetime(2023, 4, 24, 0, 0, 0)

start_date, end_date, aggregation_selection = get_general_layout(start=old_start_dt)
st.header("Tuulen ja lämpötilan korrelaatio")

# Get data from start of 2020 until 2023 Feb and save it in cache

st.markdown("Tuulivoimatuotannon valitun aggregointitason mukaisen käyttöasteen "
            "(tuulituotanto/asennettu kapasiteetti samalla ajanhetkellä) sekä keskilämpötilan välinen xy-kuvaaja "
            "kuvaa tuulen ja lämpötilan korrelaatiota. Keskilämpötila on laskettu Helsingin, Jämsän, Oulun ja "
            "Rovaniemen tuntilämpötiloista. Lämpötiladatan lähteenä on "
            "[Ilmatieteen laitos](https://www.ilmatieteenlaitos.fi/avoin-data). Dataa on käytettävissä vuoden 2018 "
            "alusta alkaen.")
st.markdown("Voit halutessasi piilottaa kuvasta eri vuosien datoja tai sovitteen klikkaamalla niitä selitteestä. "
            "Tuplaklikkauksella voit valita tietyn vuoden ainoastaan näkyviin. ")
st.markdown("Sovitteena kuvaajassa käytetään epälineaarista lokaalia regressiomallia "
            "[LOWESS](https://en.wikipedia.org/wiki/Local_regression), mikä lasketaan koko valitulle ajanjaksolle. "
            "Kuvassa näytetään myös lämpötilan ja käyttöasteen histogrammit.")

color = None

if start_date < old_start_dt.date():
    st.warning("Dataa voidaan näyttää vain vuodesta 2018 alkaen")

else:
    if st_toggle_switch("Korosta eri vuodet värein?", default_value=True, label_after=True):
        color = 'Vuosi'

    # Then take more recent data to avoid loading too much data every timer
    df = get_temperatures(new_start_dt, datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time()))
    with chart_container(df, ["Kuvaaja 📈", "Data 📄", "Lataa 📁"], ["CSV"]):
        fig = px.scatter(df, x='Keskilämpötila', y='Käyttöaste', color=color, trendline="lowess",
                         trendline_scope="overall", opacity=0.5, height=700,
                         hover_name=df.index.strftime("%d/%m/%Y %H:%M"), hover_data=['Tuulituotanto', 'Kapasiteetti'],
                         marginal_x="histogram", marginal_y="histogram")

        fig.update_layout(dict(yaxis_title='%', xaxis_autorange=True, yaxis_range=[-2, 102],
                               xaxis_title='Lämpötila', yaxis_tickformat=",.2r"))
        fig.data[-3].name = 'Sovite (LOWESS)'
        fig.data[-3].update(line_width=4, opacity=1)
        fig.data[-3].showlegend = True
        # Remove trendline from the histograms
        fig.data = [fig.data[i] for i in range(len(fig.data) - 2)]
        st.plotly_chart(fig, use_container_width=True)
