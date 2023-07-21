import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objs as go
from streamlit_extras.chart_container import chart_container
from src.fingridapi import get_data_from_FG_API_with_start_end
from src.general_functions import get_general_layout, aggregate_data
from datetime import datetime, time, timedelta
st.set_page_config(
    page_title="EnergiaData - Suomen siirtoyhteyksien tilastoja",
    page_icon="https://i.imgur.com/Kd4P3y2.png",
    layout='wide',
    initial_sidebar_state='expanded'
)



st.cache_data(show_spinner=False, max_entries=200)
def get_flows_and_capacities_df(start, end, flow_mapping):
    """
    Get the commercial flows and capacity values from Fingrid API between the start and end dates
    :param start: start date
    :param end: end date
    :return: production dataframe with demand values included
    """

    dfs = []
    for key, value in flow_mapping.items():
        df = get_data_from_FG_API_with_start_end(value, start, end)
        df.rename({'Value': key}, axis=1, inplace=True)
        dfs.append(df)

    result = pd.concat(dfs, axis=1)
    # export is given expected to be positive always
    result['Vientikapasiteetti'] = abs(result['Vientikapasiteetti'])
    result['Tuontikapasiteetti'] = result['Tuontikapasiteetti'] * -1
    return result


start_date, end_date, aggregation_selection = get_general_layout()

st.subheader('Suomen siirtoyhteyksien tilastoja')
st.markdown("Positiiviset arvot kuvaavat vientiä Suomesta. Datassa on välillä pieniä puutteita tai virheitä.")

estlink_map = {'Kaupallinen siirto': 140,
               'Vientikapasiteetti': 115,
               'Tuontikapasiteetti': 112}

fennoskan_map = {'Kaupallinen siirto': 32,
                 'Vientikapasiteetti': 27,
                 'Tuontikapasiteetti': 25}

rac_map = {'Kaupallinen siirto': 31,
           'Vientikapasiteetti': 26,
           'Tuontikapasiteetti': 24}

estlink_df = get_flows_and_capacities_df(start_date, end_date, estlink_map)
fennoskan_df = get_flows_and_capacities_df(start_date, end_date, fennoskan_map)
rac_df = get_flows_and_capacities_df(start_date, end_date, rac_map)
aggregated_estlink_df = aggregate_data(estlink_df, aggregation_selection)
tab1, tab2, tab3 = st.tabs(['Suomi - Viro', 'Suomi - Pohjois-Ruotsi (SE1)', 'Suomi - Keski-Ruotsi (SE3)'])

with tab1:
    st.markdown("EstLink")
    # Using chart_container that allows user to look into the data or download it from separate tabs
    with chart_container(aggregated_estlink_df, ["Kuvaaja 📈", "Data 📄", "Lataa 📁"], ["CSV"]):
        # Demand and production metrics and graph
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Maksimisiirto", f"{int(aggregated_estlink_df['Kaupallinen siirto'].max() + 0.5)} MW")
        with col2:
            st.metric("Keskimääräinen siirto", f"{int(aggregated_estlink_df['Kaupallinen siirto'].mean() + 0.5)} MW")
        with col3:
            st.metric("Minimisiirto", f"{int(aggregated_estlink_df['Kaupallinen siirto'].min() + 0.5)} MW")
        fig = px.line(aggregated_estlink_df, x=aggregated_estlink_df.index,
                      y=['Kaupallinen siirto', 'Vientikapasiteetti', 'Tuontikapasiteetti'],
                      title="Suomen ja Viron välinen sähkönsiirto")
        fig.update_traces(line=dict(width=2.5))
        fig.update_layout(dict(yaxis_title='MW', legend_title="Aikasarja"))
        st.plotly_chart(fig, use_container_width=True)

aggregated_rac_df = aggregate_data(rac_df, aggregation_selection)

with tab2:
    st.markdown("Suomen ja Ruotsin välinen ainoa vaihtosähköyhteys. "
                "Data sisältää myös Suomen ja Norjan välisen pienen vaihtosähköyhteyden siirron.")
    # Using chart_container that allows user to look into the data or download it from separate tabs
    with chart_container(aggregated_rac_df, ["Kuvaaja 📈", "Data 📄", "Lataa 📁"], ["CSV"]):
        # Demand and production metrics and graph

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Maksimisiirto", f"{int(aggregated_rac_df['Kaupallinen siirto'].max() + 0.5)} MW")
        with col2:
            st.metric("Keskimääräinen siirto", f"{int(aggregated_rac_df['Kaupallinen siirto'].mean() + 0.5)} MW")
        with col3:
            st.metric("Minimisiirto", f"{int(aggregated_rac_df['Kaupallinen siirto'].min() + 0.5)} MW")
        fig = px.line(aggregated_rac_df, x=aggregated_rac_df.index,
                      y=['Kaupallinen siirto', 'Vientikapasiteetti', 'Tuontikapasiteetti'],
                      title="Suomen ja Pohjois-Ruotsin (+ Norjan) välinen sähkönsiirto")
        fig.update_traces(line=dict(width=2.5))
        fig.update_layout(dict(yaxis_title='MW', legend_title="Aikasarja"))
        st.plotly_chart(fig, use_container_width=True)

aggregated_fennoskan_df = aggregate_data(fennoskan_df, aggregation_selection)

with tab3:
    st.markdown("Fenno-Skan. Korkeajännitteisiä tasasähköyhteyksiä on tällä hetkellä kaksi.")
    with chart_container(aggregated_fennoskan_df, ["Kuvaaja 📈", "Data 📄", "Lataa 📁"], ["CSV"]):
        # Demand and production metrics and graph

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Maksimisiirto", f"{int(aggregated_fennoskan_df['Kaupallinen siirto'].max() + 0.5)} MW")
        with col2:
            st.metric("Keskimääräinen siirto", f"{int(aggregated_fennoskan_df['Kaupallinen siirto'].mean() + 0.5)} MW")
        with col3:
            st.metric("Minimisiirto", f"{int(aggregated_fennoskan_df['Kaupallinen siirto'].min() + 0.5)} MW")
        fig = px.line(aggregated_fennoskan_df, x=aggregated_fennoskan_df.index,
                      y=['Kaupallinen siirto', 'Vientikapasiteetti', 'Tuontikapasiteetti'],
                      title="Suomen ja Keski-Ruotsin välinen sähkönsiirto")
        fig.update_traces(line=dict(width=2.5))
        fig.update_layout(dict(yaxis_title='MW', legend_title="Aikasarja"))
        st.plotly_chart(fig, use_container_width=True)







