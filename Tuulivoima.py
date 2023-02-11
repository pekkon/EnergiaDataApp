import plotly.subplots
import streamlit as st
from streamlit_extras.chart_container import chart_container
import plotly.express as px
import pandas as pd
import numpy as np
from src.general_functions import get_general_layout, aggregate_data
from src.fingridapi import get_data_from_FG_API_with_start_end
import datetime

st.set_page_config(
    page_title="EnergiaData - Tuuli- ja sähköjärjestelmätilastoja",
    page_icon="https://i.imgur.com/Kd4P3y2.png",
    layout='wide',
    initial_sidebar_state='expanded'
)
curr_date = datetime.datetime.now()
st.session_state['start_date_max_value'] = curr_date
st.session_state['end_date_selected'] = curr_date

@st.cache_data(show_spinner=False, max_entries=200)
def get_demand_df(start, end):
    """
    Get the demand values from Fingrid API between the start and end dates
    :param start: start date
    :param end: end date
    :return: demand dataframe
    """
    demand_df = get_data_from_FG_API_with_start_end(124, start, end)
    demand_df.rename({'Value': 'Kulutus'}, axis=1, inplace=True)
    return demand_df


@st.cache_data(show_spinner=False, max_entries=200)
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


start_date, end_date, aggregation_selection = get_general_layout()

st.subheader('Tuulivoiman tilastoja')
# Create tabs for different visualizations
tab1, tab2 = st.tabs(['Tuulivoimatuotanto ja -kapasiteetti', 'Muita tuulivoimatilastoja'])



with tab1:
    # tab1 will include visualization of wind production, capacity and
    # utilization rate during the user selected period.
    wind_df = get_wind_df(start_date, end_date)
    aggregated_wind = aggregate_data(wind_df, aggregation_selection)

    # Using chart_container that allows user to look into the data or download it from separate tabs
    with chart_container(aggregated_wind, ["Kuvaajat 📈", "Data 📄", "Lataa 📁"], ["CSV"]):
        # Wind production metrics and graph
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Maksimituotanto", f"{int(aggregated_wind['Tuulituotanto'].max() + 0.5)} MW")
        with col2:
            st.metric("Keskimääräinen tuotanto", f"{int(aggregated_wind['Tuulituotanto'].mean() + 0.5)} MW")
        with col3:
            st.metric("Minimituotanto", f"{int(aggregated_wind['Tuulituotanto'].min() + 0.5)} MW")
        fig = px.line(aggregated_wind, x=aggregated_wind.index, y=['Tuulituotanto', 'Kapasiteetti'],
                      title="Tuulivoimatuotanto ja asennettu kapasiteetti")
        fig.update_traces(line=dict(width=2.5))
        fig.update_layout(dict(yaxis_title='MW'), legend_title="Aikasarja")
        st.plotly_chart(fig, use_container_width=True)

        # Utilization rate metrics and graph
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Maksimikäyttöaste", f"{aggregated_wind['Käyttöaste'].max()} %")
        with col2:
            st.metric("Keskimääräinen käyttöaste", f"{round(aggregated_wind['Käyttöaste'].mean(), 1)} %")
        with col3:
            st.metric("Minimikäyttöaste", f"{aggregated_wind['Käyttöaste'].min()} %")

        fig = px.line(aggregated_wind, x=aggregated_wind.index, y=['Käyttöaste'],
                      title="Tuulivoimatuotannon käyttöaste (eli tuotanto/kapasiteetti)")
        fig.update_traces(line=dict(width=2.5))
        fig.update_layout(legend_title="Aikasarja", yaxis=dict(title='%', range=[0, 100]))
        st.plotly_chart(fig, use_container_width=True)




with tab2:
    # tab2 could include other visualizations or statistics, TBC


    demand_df = get_demand_df(start_date, end_date)
    demand_df['Tuulituotannon osuus kulutuksesta'] = wind_df['Tuulituotanto']/demand_df['Kulutus'] * 100
    aggregated_demand = aggregate_data(demand_df, aggregation_selection)
    # Using chart_container that allows user to look into the data or download it from separate tabs
    with chart_container(aggregated_demand, ["Kuvaajat 📈", "Data 📄", "Lataa 📁"], ["CSV"]):
        st.subheader("Tuulituotannon osuus kulutuksesta")

        # Wind production metrics and graph
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Maksimiosuus", f"{aggregated_demand['Tuulituotannon osuus kulutuksesta'].max()} %")
        with col2:
            st.metric("Keskimääräinen osuus", f"{round(aggregated_demand['Tuulituotannon osuus kulutuksesta'].mean(), 1)} %")
        with col3:
            st.metric("Minimiosuus", f"{aggregated_demand['Tuulituotannon osuus kulutuksesta'].min()} %")

        subfig = plotly.subplots.make_subplots(specs=[[{"secondary_y": True}]])

        fig = px.line(aggregated_demand, x=aggregated_demand.index, y=['Tuulituotannon osuus kulutuksesta'])
        fig2 = px.line(aggregated_demand, x=aggregated_demand.index, y=['Kulutus'])

        fig2.update_traces(yaxis="y2")

        subfig.add_traces(fig.data + fig2.data)
        subfig.layout.xaxis.title = "Time"
        subfig.layout.yaxis.title = "%"
        subfig.layout.yaxis2.title = "MW"
        subfig.layout.yaxis2.overlaying = "y"
        subfig.layout.yaxis2.tickmode = "sync"
        subfig.layout.yaxis2.tickformat = ",.2r"
        subfig.for_each_trace(lambda t: t.update(line=dict(color=t.marker.color)))
        st.plotly_chart(subfig, use_container_width=True)
