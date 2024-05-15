import plotly.subplots
import streamlit as st
from streamlit_extras.chart_container import chart_container
import plotly.express as px
import numpy as np
from src.general_functions import get_general_layout, aggregate_data
from src.fingridapi import get_data_from_fg_api_with_start_end
from src.entsoapi import get_finnish_price_data

st.set_page_config(
    page_title="EnergiaData - Tuuli- ja sähköjärjestelmätilastoja",
    page_icon="https://i.imgur.com/Kd4P3y2.png",
    layout='wide',
    initial_sidebar_state='expanded'
)


@st.cache_data(show_spinner=False, max_entries=200)
def get_demand_df(start, end):
    """
    Get the demand values from Fingrid API between the start and end dates
    :param start: start date
    :param end: end date
    :return: demand dataframe
    """
    demand_df = get_data_from_fg_api_with_start_end(124, start, end)
    demand_df.rename({'Value': 'Kulutus'}, axis=1, inplace=True)
    return demand_df


def get_wind_df(start, end):
    """
    Get the wind production and capacity values from Fingrid API between the start and end dates.
    Calculates the utilization rate
    :param start: start date
    :param end: end date
    :return: wind dataframe
    """

    df = get_data_from_fg_api_with_start_end(75, start, end)
    df.rename({'Value': 'Tuulituotanto'}, axis=1, inplace=True)

    wind_capacity = get_data_from_fg_api_with_start_end(268, start, end)
    # Fixing issues in the API capacity (sometimes capacity is missing and API gives low value)
    wind_capacity.loc[wind_capacity['Value'] < wind_capacity['Value'].shift(-24), 'Value'] = np.NaN
    df['Kapasiteetti'] = wind_capacity['Value']
    # Due to issues with input data with strange timestamps, we need to resample the data
    df = df.resample('H')
    # Interpolate missing values linearly
    df = df.interpolate()

    df['Käyttöaste'] = df['Tuulituotanto'] / df['Kapasiteetti'] * 100
    return df.round(1)


start_date, end_date, aggregation_selection = get_general_layout()

st.subheader('Tuulivoiman tilastoja')
# Create tabs for different visualizations
tab1, tab2, tab3 = st.tabs(['Tuulivoimatuotanto ja -kapasiteetti', 'Tuulen osuus kulutuksesta',
                            'Tuulivoiman saama hinta'])

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
            st.metric("Maksimituotanto", f"{round(aggregated_wind['Tuulituotanto'].max(), 1)} MW")
        with col2:
            st.metric("Keskimääräinen tuotanto", f"{round(aggregated_wind['Tuulituotanto'].mean(), 1)} MW")
        with col3:
            st.metric("Minimituotanto", f"{round(aggregated_wind['Tuulituotanto'].min(), 1)} MW")
        st.markdown("**Tuulivoimatuotanto ja asennettu kapasiteetti**")
        fig = px.scatter(aggregated_wind, x=aggregated_wind.index, y=['Tuulituotanto', 'Kapasiteetti'],
                         trendline='expanding', trendline_options=dict(function="max"))
        fig.update_traces(mode='lines')
        fig.data[1].update(dict(name='Tuulivoimatuotannon ennätys', legendgroup=None, showlegend=True,
                                visible='legendonly', line_color='#FF4B4B'))
        # Remove trend line for max capacity
        fig.data = fig.data[:-1]
        fig.update_traces(line=dict(width=2.5))
        fig.update_layout(dict(yaxis_title='MW'), legend_title="Aikasarja")
        fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)

        # Utilization rate metrics and graph
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Maksimikäyttöaste", f"{aggregated_wind['Käyttöaste'].max()} %")
        with col2:
            st.metric("Keskimääräinen käyttöaste", f"{round(aggregated_wind['Käyttöaste'].mean(), 1)} %")
        with col3:
            st.metric("Minimikäyttöaste", f"{aggregated_wind['Käyttöaste'].min()} %")
        st.markdown("**Tuulivoimatuotannon käyttöaste (eli tuotanto/kapasiteetti)**")
        fig = px.line(aggregated_wind, x=aggregated_wind.index, y=['Käyttöaste'])
        fig.update_traces(line=dict(width=2.5))
        fig.update_layout(legend_title="Aikasarja", yaxis=dict(title='%', range=[0, 100]))
        fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
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
        subfig.layout.xaxis.title = "Aika"
        subfig.layout.yaxis.title = "%"
        subfig.layout.yaxis2.title = "MW"
        subfig.layout.yaxis2.overlaying = "y"
        subfig.layout.yaxis2.tickmode = "sync"
        subfig.layout.yaxis2.tickformat = ".2r"
        subfig.layout.yaxis2.hoverformat = ".1f"
        subfig.for_each_trace(lambda t: t.update(line=dict(color=t.marker.color)))
        subfig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(subfig, use_container_width=True)

with tab3:
    price_df = get_finnish_price_data(start_date, end_date)
    st.subheader("Tuulituotannon saama hinta valitulla aikavälillä.")
    wind_price_df = wind_df.copy()
    length = len(wind_price_df)
    wind_price_df['Hinta'] = price_df.values[:length]
    wind_price_df['CP'] = wind_price_df['Hinta'] * wind_price_df['Tuulituotanto']
    col1, col2, col3 = st.columns(3)
    with col1:
        price_avg = price_df.mean()
        st.metric("Sähkön keskihinta:", f"{round(price_avg, 1)} €/MWh")
    with col2:
        cp_avg = wind_price_df['CP'].sum()/wind_price_df['Tuulituotanto'].sum()
        st.metric("Tuulivoiman saama hinta:",
                  f"{round(cp_avg, 1)} €/MWh")
    with col3:
        st.metric("Suhde keskihintaan:", f"{round(cp_avg/price_avg * 100, 1) } %")
    monthly_averages = wind_price_df[['Tuulituotanto', 'Hinta', 'CP']].resample('M').agg({'Tuulituotanto': np.sum, 'Hinta': np.mean, 'CP': np.sum})
    monthly_averages.index = monthly_averages.index.strftime('%Y-%m')
    monthly_averages['Keskihinta €/MWh'] = round(monthly_averages['Hinta'] , 1)
    monthly_averages['Tuulen saama hinta €/MWh'] = round(monthly_averages['CP'] / monthly_averages['Tuulituotanto'], 1)
    monthly_averages['Suhde (%)'] = round(monthly_averages['Tuulen saama hinta €/MWh']/monthly_averages['Hinta'] * 100, 1)
    st.markdown("**Tuulivoiman kuukausittaisen saaman hinnan suhde kuukauden keskihintaan:**")
    subfig = plotly.subplots.make_subplots(specs=[[{"secondary_y": True}]])
    fig1 = px.bar(monthly_averages, y=['Keskihinta €/MWh', 'Tuulen saama hinta €/MWh'], barmode='group',
                 height=400)
    fig2 = px.line(x=monthly_averages.index, y=monthly_averages['Suhde (%)'])
    fig2.update_traces(line_color='red', line_width=1, legendgroup=None, showlegend=True, name='Suhde (%)')
    fig2.update_traces(yaxis="y2")
    subfig.add_traces(fig1.data + fig2.data)
    subfig.layout.xaxis.title = "Aika"
    subfig.layout.yaxis.title = "€/MWh"
    subfig.layout.yaxis2.title = "%"
    subfig.update_layout(yaxis2=dict(range=[0,100]))
    subfig.layout.yaxis2.overlaying = "y"
    subfig.layout.yaxis2.tickmode = "sync"
    subfig.layout.yaxis2.tickformat = ".1f"
    subfig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(subfig, use_container_width=True)
