import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objs as go
import plotly
from streamlit_extras.chart_container import chart_container
from src.fingridapi import get_data_from_fg_api_with_start_end
from src.general_functions import get_general_layout, aggregate_data
from fmiopendata.wfs import download_stored_query
from datetime import datetime, time, timedelta
from src.entsoapi import get_price_data
st.set_page_config(
    page_title="EnergiaData - Tuuli- ja sähköjärjestelmätilastoja",
    page_icon="https://i.imgur.com/Kd4P3y2.png",
    layout='wide',
    initial_sidebar_state='expanded'
)


@st.cache_data(show_spinner=False, max_entries=200)
def get_production_and_demand_df(start, end):
    """
    Get the production and  demand values from Fingrid API between the start and end dates
    :param start: start date
    :param end: end date
    :return: production dataframe with demand values included
    """
    demand_df = get_data_from_fg_api_with_start_end(124, start, end)
    demand_df.rename({'Value': 'Kulutus'}, axis=1, inplace=True)
    production_df = get_data_from_fg_api_with_start_end(74, start, end)
    production_df.rename({'Value': 'Tuotanto'}, axis=1, inplace=True)
    production_df['Kulutus'] = demand_df['Kulutus']
    production_df['Tase'] = production_df['Tuotanto'] - production_df['Kulutus']
    return production_df

st.cache_data(show_spinner=False, max_entries=200)
def get_generations_df(start, end):
    """
    Get the generation values from Fingrid API between the start and end dates
    :param start: start date
    :param end: end date
    :return: production dataframe with demand values included
    """
    generation_mapping = {'Ydinvoima': 188,
                          'Kaukolämmön yhteistuotanto': 201,
                          'Teollisuuden yhteistuotanto': 202,
                          'Muu tuotanto': 205,
                          'Tuulivoima': 181,
                          'Vesivoima': 191,
                          'Nettotuonti/-vienti': 194,
                          'Tuotanto': 192,
                          'Kulutus': 193}

    dfs = []
    for key, value in generation_mapping.items():
        df = get_data_from_fg_api_with_start_end(value, start, end)
        df.rename({'Value': key}, axis=1, inplace=True)
        dfs.append(df)

    result = pd.concat(dfs, axis=1)
    # Solar production is not available from API but can be calculated
    solar = result['Tuotanto'] - result[result.columns[0:6]].sum(axis=1)
    result.insert(5, 'Aurinkovoima', solar)

    return result


start_date, end_date, aggregation_selection = get_general_layout()

st.subheader('Suomen tuotanto- ja kulutustilastoja')

prod_dem_df = get_production_and_demand_df(start_date, end_date)
aggregated_df = aggregate_data(prod_dem_df, aggregation_selection)
tab1, tab2 = st.tabs(['Sähkön tuotanto ja kulutus', 'Suomen tuotantojakauma (3min)'])

with tab1:
    # Using chart_container that allows user to look into the data or download it from separate tabs
    with chart_container(aggregated_df, ["Kuvaajat 📈", "Data 📄", "Lataa 📁"], ["CSV"]):
        # Demand and production metrics and graph
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Maksimikulutus", f"{int(aggregated_df['Kulutus'].max() + 0.5)} MW")
            st.metric("Maksimituotanto", f"{int(aggregated_df['Tuotanto'].max() + 0.5)} MW")
        with col2:
            st.metric("Keskimääräinen kulutus", f"{int(aggregated_df['Kulutus'].mean() + 0.5)} MW")
            st.metric("Keskimääräinen tuotanto", f"{int(aggregated_df['Tuotanto'].mean() + 0.5)} MW")
        with col3:
            st.metric("Minimikulutus", f"{int(aggregated_df['Kulutus'].min() + 0.5)} MW")
            st.metric("Minimituotanto", f"{int(aggregated_df['Tuotanto'].min() + 0.5)} MW")
        fig = px.line(aggregated_df, x=aggregated_df.index, y=['Tuotanto', 'Kulutus'],
                      title="Suomen tuotanto ja kulutus")
        fig.update_traces(line=dict(width=2.5))
        fig.update_layout(dict(yaxis_title='MW', legend_title="Aikasarja", yaxis_tickformat=",.2r"))
        st.plotly_chart(fig, use_container_width=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Maksiminettotase", f"{int(aggregated_df['Tase'].max() + 0.5)} MW")
        with col2:
            st.metric("Keskimääräinen nettotase", f"{int(aggregated_df['Tase'].mean() + 0.5)} MW")
        with col3:
            st.metric("Miniminettotase", f"{int(aggregated_df['Tase'].min() + 0.5)} MW")

        fig2 = px.scatter(aggregated_df, x=aggregated_df.index, y=['Tase'],
                      title="Suomen nettovienti(+)/-tuonti(-)", trendline="ols", trendline_color_override='#0068C9')
        fig2.update_traces(mode='lines')
        fig2.update_traces(line=dict(width=2.5))
        fig2.data[1].name = 'Trendi'
        fig2.data[1].showlegend = True
        fig2.update_layout(dict(yaxis_title='MW'), legend_title="Aikasarja")
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Kauppatase")
    st.write("Kauppatase = Nettotase * Suomen aluehinta samana ajankohtana")
    price_df = get_price_data(start_date, end_date, prod_dem_df.index)
    trade_balance = prod_dem_df.copy()
    trade_balance['Hinta'] = price_df.values
    trade_balance['Kauppatase'] = trade_balance['Tase'] * trade_balance['Hinta']
    aggregated_df = aggregate_data(trade_balance, aggregation_selection, 'sum')
    st.metric("Kauppatase valitulla aikavälillä:", f"{round(aggregated_df['Kauppatase'].sum()/1000000, 1)} M€")
    fig = px.line(aggregated_df, x=aggregated_df.index, y='Kauppatase',
                  title="Suomen kauppatase")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader('Suomen tuotantorakenne')
    if end_date - start_date > timedelta(28):
        st.warning('Valitse alle neljän viikon aikajakso, jos haluat tarkastella tuotantorakennetta halutulta'
                   ' aikaväliltä. Alla olevassa kuvassa näytetään dataa valitun aikajakson viimeiseltä neljältä viikolta.')
        start_date = end_date - timedelta(28)
    generation_df = get_generations_df(start_date, end_date)
    # Change net balance sign for visualization purposes
    generation_df['Nettotuonti/-vienti'] = generation_df['Nettotuonti/-vienti'] * -1
    #aggregated_df = aggregate_data(generation_df, aggregation_selection)
    with chart_container(generation_df, ["Kuvaaja 📈", "Data 📄", "Lataa 📁"], ["CSV"]):
        fig = px.area(generation_df, x=generation_df.index, y=generation_df.columns[:-2])
        fig.add_trace(go.Scatter(x=generation_df.index, y=generation_df['Tuotanto'], mode='lines'))
        fig.add_trace(go.Scatter(x=generation_df.index, y=generation_df['Kulutus'], mode='lines'))
        # Adjust coloring of lines
        # CHP
        fig.data[1]['line_color'] = "#000006"
        # Solar
        fig.data[5]['line_color'] = "#000007"
        # Hydro
        fig.data[6]['line_color'] = "#000002"
        fig.data[-1].update(dict(name='Kulutus', legendgroup=None, showlegend=True,
                            visible='legendonly'))
        fig.data[-2].update(dict(name='Tuotanto', legendgroup=None, showlegend=True,
                                 visible='legendonly', line_color='#FF4B4B'))
        fig.data[-3].update(dict(visible='legendonly'))
        fig.update_layout(legend_title="Tuotantomuoto", yaxis=dict(title='MW'))
        st.plotly_chart(fig, use_container_width=True)




