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

    if new_start_time <= pd.to_datetime(end):
        new_df = get_data_from_fg_api_with_start_end(75, new_start_time, end)

        new_df.rename({'Value': 'Tuulituotanto'}, axis=1, inplace=True)

        wind_capacity = get_data_from_fg_api_with_start_end(268, new_start_time, end)
        # Fixing issues in the API capacity (sometimes capacity is missing and API gives low value)
        wind_capacity.loc[wind_capacity['Value'] < wind_capacity['Value'].shift(-24), 'Value'] = np.NaN
        new_df['Kapasiteetti'] = wind_capacity['Value']
        # Due to issues with input data with strange timestamps, we need to resample the data
        new_df = new_df.resample('H')
        # Interpolate missing values linearly
        new_df = new_df.interpolate('time')
        new_df = pd.concat([old_df, new_df])
        duplicates = new_df.index.duplicated()
        if duplicates.any():
            print("There are duplicate index values.")

            # Option 1: Remove duplicates
            df_no_duplicates = new_df[~duplicates]

            # Option 2: Aggregate duplicates
            new_df = new_df.groupby(new_df.index).last()
        new_df.to_csv('./data/old_wind_corr_data.csv')

    else:
        new_df = old_df
    new_df['Käyttöaste'] = new_df['Tuulituotanto'] / new_df['Kapasiteetti'] * 100
    # Filter wind data based on the selected date if we have more data already downloaded
    start = pd.to_datetime(start)
    end = pd.to_datetime(end)

    return new_df.loc[start:end].round(1)


def get_temperatures(start_time, end_date):
    old_df = pd.read_csv('./data/old_temperatures.csv')
    old_df['Aikaleima'] = pd.to_datetime(old_df['Aikaleima'])
    old_df.set_index(['Aikaleima'], inplace=True)
    new_start_time = check_previous_data(old_df, start_time)

    # Fetch new data only if there's a gap between old data and end_time
    if new_start_time <= pd.to_datetime(end_date):
        new_df = temperatures(new_start_time, end_date)
    else:
        new_df = pd.DataFrame()
    end_time = pd.to_datetime(end_date).tz_localize('Europe/Helsinki')
    start_time = pd.to_datetime(start_time).tz_localize('Europe/Helsinki')
    # Combine old and new data
    temperature_df = pd.concat([old_df, new_df])
    temperature_df.to_csv('./data/old_temperatures.csv')
    wind_df = get_wind_df(start_time, end_time)
    #wind_df.index = pd.to_datetime(wind_df.index)
    temperature_df['Keskilämpötila'] = temperature_df.mean(axis=1)
    temperature_df.index = temperature_df.index.tz_localize('UTC')
    temperature_df.index = temperature_df.index.tz_convert('Europe/Helsinki')
    filtered_temp_df = temperature_df.loc[start_time:end_time]
    wind_df.index = pd.to_datetime(wind_df.index, utc=True)
    wind_df.index = wind_df.index.tz_convert('Europe/Helsinki')
    filtered_wind_df = wind_df.loc[start_time:end_time]

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

tab1, tab2, tab3, tab4 = st.tabs(['Tuulivoiman ja lämpötilan korrelaatio',
                                  'Tuulivoiman, lämpötilan ja sähkön hinnan korrelaatio',
                                  'Tuulivoiman lämpökartta vuorokauden tunneilla',
                                  'Sähkön hinnan lämpökartta vuorokauden tunneilla'])
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
        df = get_temperatures(old_start_dt, end_date)
        aggregated_wind = aggregate_data(df, aggregation_selection)
        aggregated_wind['Vuosi'] = aggregated_wind.index.year.astype(str)
        with chart_container(aggregated_wind, ["Kuvaaja 📈", "Data 📄", "Lataa 📁"], ["CSV"]):
            fig = px.scatter(aggregated_wind, x='Keskilämpötila', y='Käyttöaste', color=color, trendline="lowess",
                             trendline_scope="overall", opacity=0.5, height=700,
                             hover_name=aggregated_wind.index.strftime("%d/%m/%Y %H:%M"), hover_data=['Tuulituotanto', 'Kapasiteetti'])

            fig.update_layout(dict(yaxis_title='%', xaxis_autorange=True, yaxis_range=[-2, 102],
                                   xaxis_title='Lämpötila', yaxis_tickformat=".2r", yaxis_hoverformat=".1f"))
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            fig.data[-1].name = 'Sovite (LOWESS)'
            fig.data[-1].update(line_width=4, opacity=1)
            fig.data[-1].showlegend = True
            st.plotly_chart(fig, use_container_width=True)

with tab2:

    st.header("Tuulen, lämpötilan ja sähkön hinnan korrelaatio")
    price_df = get_finnish_price_data(start_date, end_date + datetime.timedelta(days=1))

    df.index = df.index.tz_localize(None)
    price_df.index = pd.to_datetime(price_df.index, utc=True).tz_localize(None)
    df = pd.merge_asof(df, price_df, left_index=True, right_index=True)
    df = df.rename({'FI': 'Hinta'}, axis=1)
    temp_price = aggregate_data(df, aggregation_selection)
    temp_price['Vuosi'] = temp_price.index.year.astype(str)


    st.markdown("Tuulivoimatuotannon valitun aggregointitason mukaisen käyttöasteen "
                "(tuulituotanto/asennettu kapasiteetti samalla ajanhetkellä), lämpötilan sekä sähkön hinnan välinen "
                "xyz-kuvaaja kuvaa tuulen, lämpötilan ja sähkön hinnan välistä korrelaatiota.")
    st.markdown("Voit halutessasi piilottaa kuvasta eri vuosien datoja tai sovitteen klikkaamalla niitä selitteestä. "
                "Tuplaklikkauksella voit valita tietyn vuoden ainoastaan näkyviin. ")

    color = None


    if st_toggle_switch("Korosta eri vuodet värein?", default_value=True, label_after=True, key="tab2"):
        color = 'Vuosi'

    range_of_price3d = st.slider("Valitse hintarajat kuvaajalle:", value=(0, 100), min_value=-500, max_value=3000,
                              step=10)

    fig = px.scatter_3d(temp_price, x='Keskilämpötila', y='Hinta', z='Käyttöaste', color=color, opacity=0.3,
                        height=1000, range_y=range_of_price3d, hover_name=temp_price.index.strftime("%d/%m/%Y %H:%M"))

    # fig.update_layout(dict(yaxis_title='Hinta €/MWh', xaxis_autorange=True,
    #                        xaxis_title='Lämpötila', yaxis_tickformat=",.1r", yaxis_hoverformat=",.1f"))
    # fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    # fig.data[-1].name = 'Sovite (LOWESS)'
    # fig.data[-1].update(line_width=4, opacity=1)
    # fig.data[-1].showlegend = True
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.header("Tuulivoiman lämpökartta vuorokauden tunneilla")
    st.markdown("Lämpökartta kuvaa valitun aikaikkunan sisällä laskettua keskimääräistä tuulivoiman käyttöastetta.")

    df['Tunti'] = df.index.hour.astype(str)
    df['Päivä'] = df.index.date.astype(str)

    range_of_prod = st.slider("Valitse käyttöasterajat kuvaajalle:", value=(0, 100), min_value=0, max_value=100,
                               step=5)
    fig = px.density_heatmap(df, z='Käyttöaste', y='Tunti', x='Päivä', histfunc='avg',height=600,
                             color_continuous_scale=px.colors.diverging.balance, range_color=list(range_of_prod))


    if aggregation_selection == 'Viikko':
        agg = 604800000
    elif aggregation_selection == 'Kuukausi':
        agg = 'M1'
    else:
        agg = 'D1'
    fig.update_traces(xbins_size=agg)
    fig.update_layout(dict(xaxis_autorange=True, legend_title="Aikasarja", xaxis_title='Aika'))
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig.layout['coloraxis']['colorbar']['title']['text'] = 'Käyttöaste %'
    fig.data[0]['hovertemplate'] = 'Päivä=%{x}<br>Tunti=%{y}<br>Käyttöaste=%{z:.1f}%<extra></extra>'
    st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.header("Sähkön hinnan lämpökartta vuorokauden tunneilla")
    st.markdown("Lämpökartta kuvaa valitun aikaikkunan sisällä laskettua keskimääräistä sähkön hintaa.")

    price_df.index = pd.to_datetime(price_df.index, utc=True)
    price_df = pd.DataFrame(price_df)
    price_df['Tunti'] = price_df.index.hour.astype(str)
    price_df['Päivä'] = price_df.index.date.astype(str)
    price_df.rename({'FI': 'Hinta'}, axis=1, inplace=True)
    range_of_price = st.slider("Valitse hintarajat kuvaajalle:", value=(0, 200), min_value=-100, max_value=500,
                               step=10)
    fig = px.density_heatmap(price_df, z='Hinta', y='Tunti', x='Päivä', histfunc='avg', height=600,
                             range_color=list(range_of_price), color_continuous_scale=px.colors.diverging.balance)

    if aggregation_selection == 'Viikko':
        agg = 604800000
    elif aggregation_selection == 'Kuukausi':
        agg = 'M1'
    else:
        agg = 'D1'
    fig.update_traces(xbins_size=agg)
    fig.update_layout(dict(xaxis_autorange=True, legend_title="Aikasarja", xaxis_title='Aika'))
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig.layout['coloraxis']['colorbar']['title']['text'] = 'Hinta'
    fig.data[0]['hovertemplate'] = 'Päivä=%{x}<br>Tunti=%{y}<br>Hinta=%{z:.1f}<extra></extra>'
    st.plotly_chart(fig, use_container_width=True)