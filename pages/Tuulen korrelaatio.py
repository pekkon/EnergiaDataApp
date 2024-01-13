import plotly.subplots
import streamlit as st
from streamlit_extras.chart_container import chart_container
from streamlit_extras.toggle_switch import st_toggle_switch
import plotly.express as px
import pandas as pd
import numpy as np
from src.general_functions import get_general_layout, aggregate_data, check_previous_data
from src.fmi_api import temperatures
from src.fingridapi import get_data_from_fg_api_with_start_end
from src.entsoapi import get_finnish_price_data
import datetime



@st.cache_data(show_spinner=False, max_entries=200, persist=True)
def get_wind_df(start, end):
    """
    Get the wind production and capacity values from Fingrid API between the start and end dates.
    Calculates the utilization rate
    :param start: start date
    :param end: end date
    :return: wind dataframe
    """
    old_df = pd.read_csv('./data/old_wind_corr_data.csv')
    old_df['Aikaleima'] = pd.to_datetime(old_df['Aikaleima'])
    old_df.set_index(['Aikaleima'], inplace=True)
    new_start_time = check_previous_data(old_df, start)
    if new_start_time.date() < end:
        new_df = get_data_from_fg_api_with_start_end(75, new_start_time, end)

        new_df.rename({'Value': 'Tuulituotanto'}, axis=1, inplace=True)

        wind_capacity = get_data_from_fg_api_with_start_end(268, start, end)
        # Fixing issues in the API capacity (sometimes capacity is missing and API gives low value)
        wind_capacity.loc[wind_capacity['Value'] < wind_capacity['Value'].shift(-24), 'Value'] = np.NaN
        new_df['Kapasiteetti'] = wind_capacity['Value']

        # Due to issues with input data with strange timestamps, we need to resample the data
        new_df = new_df.resample('H')
        # Interpolate missing values linearly
        new_df = new_df.interpolate()
        new_df = pd.concat([old_df, new_df])
        new_df.to_csv('./data/old_wind_corr_data.csv')

    else:
        new_df = old_df
    new_df['Käyttöaste'] = new_df['Tuulituotanto'] / new_df['Kapasiteetti'] * 100
    # Filter wind data based on the selected date if we have more data already downloaded
    start = pd.to_datetime(start).tz_localize(None)
    end = pd.to_datetime(end).tz_localize(None)
    return new_df.loc[start:end].round(1)


@st.cache_data(show_spinner=False, max_entries=200, persist=True)
def get_temperatures(start_time, end_time):
    old_df = pd.read_csv('./data/old_temperatures.csv')
    old_df['Aikaleima'] = pd.to_datetime(old_df['Aikaleima'])
    old_df.set_index(['Aikaleima'], inplace=True)
    new_start_time = check_previous_data(old_df, start_time)
    # Fetch new data only if there's a gap between old data and end_time
    if new_start_time <= pd.to_datetime(end_time):
        new_df = temperatures(new_start_time, end_time)
    else:
        new_df = pd.DataFrame()

    # Combine old and new data
    temperature_df = pd.concat([old_df, new_df])
    temperature_df.to_csv('./data/old_temperatures.csv')
    wind_df = get_wind_df(datetime.date(2018, 1, 1), end_date)
    temperature_df['Keskilämpötila'] = temperature_df.mean(axis=1)
    filtered_temp_df = temperature_df.loc[start_date:end_date].iloc[:-1]
    filtered_wind_df = wind_df.loc[start_date:end_date].iloc[:-1]
    filtered_df = pd.merge_asof(filtered_temp_df, filtered_wind_df, left_index=True, right_index=True)
    return filtered_df[pd.to_datetime(start_time):pd.to_datetime(end_time)]

st.set_page_config(
    page_title="EnergiaData - Tuuli- ja sähköjärjestelmätilastoja",
    page_icon="https://i.imgur.com/Kd4P3y2.png",
    layout='wide',
    initial_sidebar_state='expanded'
)

old_start_dt= datetime.datetime(2018, 1, 1, 0, 0, 0)


start_date, end_date, aggregation_selection = get_general_layout(start=old_start_dt)

tab1, tab2 = st.tabs(['Tuulivoiman ja lämpötilan korrelaatio', 'Tuulivoiman ja sähkön hinnan korrelaatio'])
with tab1:
    st.header("Tuulen ja lämpötilan korrelaatio")



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
        df = get_temperatures(old_start_dt, datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time()))
        aggregated_wind = aggregate_data(df, aggregation_selection)
        aggregated_wind['Vuosi'] = aggregated_wind.index.year.astype(str)
        with chart_container(aggregated_wind, ["Kuvaaja 📈", "Data 📄", "Lataa 📁"], ["CSV"]):
            fig = px.scatter(aggregated_wind, x='Keskilämpötila', y='Käyttöaste', color=color, trendline="lowess",
                             trendline_scope="overall", opacity=0.5, height=700,
                             hover_name=aggregated_wind.index.strftime("%d/%m/%Y %H:%M"), hover_data=['Tuulituotanto', 'Kapasiteetti'],
                             marginal_x="histogram", marginal_y="histogram")

            fig.update_layout(dict(yaxis_title='%', xaxis_autorange=True, yaxis_range=[-2, 102],
                                   xaxis_title='Lämpötila', yaxis_tickformat=",.2r", yaxis_hoverformat=",.1f"))
            fig.data[-3].name = 'Sovite (LOWESS)'
            fig.data[-3].update(line_width=4, opacity=1)
            fig.data[-3].showlegend = True
            # Remove trendline from the histograms
            fig.data = [fig.data[i] for i in range(len(fig.data) - 2)]
            st.plotly_chart(fig, use_container_width=True)
with tab2:

    st.header("Tuulen ja sähkön hinnan korrelaatio")
    wind_df = get_wind_df(start_date, end_date)

    price_df = get_finnish_price_data(start_date, end_date + datetime.timedelta(days=1))
    length = len(wind_df)
    wind_df['Hinta'] = price_df.values[0:length]

    agg_wind = aggregate_data(wind_df, aggregation_selection)
    agg_wind['Vuosi'] = agg_wind.index.year.astype(str)

    st.markdown("Tuulivoimatuotannon valitun aggregointitason mukaisen käyttöasteen "
                "(tuulituotanto/asennettu kapasiteetti samalla ajanhetkellä) sekä sähkön hinnan välinen xy-kuvaaja "
                "kuvaa tuulen ja sähkön hinnan korrelaatiota.")
    st.markdown("Voit halutessasi piilottaa kuvasta eri vuosien datoja tai sovitteen klikkaamalla niitä selitteestä. "
                "Tuplaklikkauksella voit valita tietyn vuoden ainoastaan näkyviin. ")
    st.markdown("Sovitteena kuvaajassa käytetään epälineaarista lokaalia regressiomallia "
                "[LOWESS](https://en.wikipedia.org/wiki/Local_regression), mikä lasketaan koko valitulle ajanjaksolle. "
                "Kuvassa näytetään myös sähkön hinnan ja käyttöasteen histogrammit.")

    color = None

    with chart_container(agg_wind, ["Kuvaaja 📈", "Data 📄", "Lataa 📁"], ["CSV"]):
        if st_toggle_switch("Korosta eri vuodet värein?", default_value=True, label_after=True, key="tab2"):
            color = 'Vuosi'

        fig = px.scatter(agg_wind, x='Käyttöaste', y='Hinta', color=color, trendline="lowess",
                         trendline_scope="overall", opacity=0.6, height=1000,
                         hover_name=agg_wind.index.strftime("%d/%m/%Y %H:%M"),
                         hover_data=['Tuulituotanto', 'Kapasiteetti', 'Hinta'],
                         marginal_x="histogram", marginal_y="histogram")

        fig.update_layout(dict(yaxis_title='Hinta €/MWh', yaxis_autorange=True, xaxis_range=[-1, 101],
                               xaxis_title='%', xaxis_tickformat=",.2r"))
        fig.data[-3].name = 'Sovite (LOWESS)'
        fig.data[-3].update(line_width=4, opacity=1)
        fig.data[-3].showlegend = True
        # Remove trendline from the histograms
        fig.data = [fig.data[i] for i in range(len(fig.data) - 2)]
        st.plotly_chart(fig, use_container_width=True)
