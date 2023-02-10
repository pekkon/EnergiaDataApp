import streamlit as st
from streamlit_extras.chart_container import chart_container
from streamlit_extras.mention import mention
import plotly.express as px
import pandas as pd
import numpy as np
import datetime
from src.fingridapi import get_data_from_FG_API_with_start_end
from streamlit_extras.buy_me_a_coffee import button

st.set_page_config(
    page_title="EnergiaData - Tuuli- ja sähköjärjestelmätilastoja",
    page_icon="https://i.imgur.com/Kd4P3y2.png",
    layout='wide',
    initial_sidebar_state='expanded'
)


@st.cache_data(show_spinner=False)
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


@st.cache_data(show_spinner=False)
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


@st.cache_data(show_spinner=False)
def aggregate_data(df, aggregation):
    """
    Aggregates the given data based on user selected aggregation level
    :param df: dataframe
    :param aggregation: aggregation level
    :return: aggregated dataframe
    """
    if aggregation == 'Päivä':
        agg = 'D'
    elif aggregation == 'Viikko':
        agg = 'W'
    elif aggregation == 'Kuukausi':
        agg = 'M'
    else:
        agg = 'H'
    return wind_df.resample(agg).mean().round(1)


# Start of the page
st.title('EnergiaData (tämä kuvana)')
st.image('https://i.imgur.com/AzAQTPr.png', width=300)
st.subheader('Tuulivoiman tilastoja')

# Setup sidebar settings
st.sidebar.info("Valitse aikaikkuna 📆")
start_date = st.sidebar.date_input("Päivä alkaen", datetime.date(2023, 1, 1))
end_date = st.sidebar.date_input("Päivä saakka", datetime.datetime.now(), key="end_date_selection")
aggregation_selection = st.sidebar.radio('Valitse aggregointitaso 🕑', ['Tunti', 'Päivä', 'Viikko', 'Kuukausi'])

# Create tabs for different visualizations
tab1, tab2 = st.tabs(['Tuulivoimatuotanto ja -kapasiteetti', 'Muita tuulivoimatilastoja'])

with tab1:
    """
    tab1 will include visualization of wind production, capacity and 
    utilization rate during the user selected period.
    """
    wind_df = get_wind_df(start_date, end_date)
    aggregated_wind = aggregate_data(wind_df, aggregation_selection)

    #Using chart_container that allows user to look into the data or download it from separate tabs
    with chart_container(aggregated_wind, ["Kuvaajat 📈", "Data 📄","Lataa 📁"], ["CSV"]):
        # Wind production metrics and graph
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Maksimituotanto", f"{int(aggregated_wind['Tuulituotanto'].max() + 0.5)} MW")
        with col2:
            st.metric("Keskituotanto", f"{int(aggregated_wind['Tuulituotanto'].mean() + 0.5)} MW")
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
            st.metric("Maksimikäyttöaste", f"{aggregated_wind['Käyttöaste'].max() } %")
        with col2:
            st.metric("Keskikäyttöaste", f"{round(aggregated_wind['Käyttöaste'].mean(), 1)} %")
        with col3:
            st.metric("Minimikäyttöaste", f"{aggregated_wind['Käyttöaste'].min()} %")

        fig = px.line(aggregated_wind, x=aggregated_wind.index, y=['Käyttöaste'],
                      title="Tuulivoimatuotannon käyttöaste (eli tuotanto/kapasiteetti)")
        fig.update_traces(line=dict(width=2.5))
        fig.update_layout(legend_title="Aikasarja", yaxis=dict(title='%', range=[0, 100]))
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    """
    tab2 could include other visualizations or statistics, TBC
    """
    st.write("Tähän muita mahdollisia kuvaajia tai tilastoja")

# Add contact info and other information to the end of sidebar
with st.sidebar:
    mention(
        label="EnergiaData-sovelluksen lähdekoodi",
        icon="github",
        url="https://github.com/pekkon/EnergiaDataApp"
    )
    st.subheader("Ota yhteyttä:")

    mention(
        label="Pekko Niemi",
        icon="twitter",
        url="https://twitter.com/PekkoNiemi"
    )

    mention(
        label="EnergiaBotti",
        icon="twitter",
        url="https://twitter.com/EnergiaBotti"
    )

    button("pekko", False, "Buy me a pizza", "🍕")

    st.write(f'Datalähteenä Fingridin avoin data: data.fingrid.fi')