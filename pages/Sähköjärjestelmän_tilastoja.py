import streamlit as st
import plotly.express as px
import plotly
from streamlit_extras.chart_container import chart_container
from src.fingridapi import get_data_from_FG_API_with_start_end
from src.general_functions import get_general_layout, aggregate_data


st.set_page_config(
    page_title="EnergiaBotti - Tuuli- ja sähköjärjestelmätilastoja",
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
    demand_df = get_data_from_FG_API_with_start_end(124, start, end)
    demand_df.rename({'Value': 'Kulutus'}, axis=1, inplace=True)
    production_df = get_data_from_FG_API_with_start_end(74, start, end)
    production_df.rename({'Value': 'Tuotanto'}, axis=1, inplace=True)
    production_df['Kulutus'] = demand_df['Kulutus']
    production_df['Tase'] = production_df['Tuotanto'] - production_df['Kulutus']
    return production_df


start_date, end_date, aggregation_selection = get_general_layout()
st.subheader('Suomen tuotanto- ja kulutustilastoja')

prod_dem_df = get_production_and_demand_df(start_date, end_date)
aggregated_df = aggregate_data(prod_dem_df, aggregation_selection)

# Using chart_container that allows user to look into the data or download it from separate tabs
with chart_container(aggregated_df, ["Kuvaajat 📈", "Data 📄", "Lataa 📁"], ["CSV"]):
    # Production and demand graphs
    fig = px.line(aggregated_df, x=aggregated_df.index, y=['Tuotanto', 'Kulutus'],
                  title="Suomen tuotanto ja kulutus")
    fig.update_traces(line=dict(width=2.5))
    fig.update_layout(dict(yaxis_title='MW', legend_title="Aikasarja", yaxis_tickformat=",.2r"))
    st.plotly_chart(fig, use_container_width=True)

    fig2 = px.scatter(aggregated_df, x=aggregated_df.index, y=['Tase'],
                  title="Suomen nettovienti(+)/-tuonti(-)", trendline="ols", trendline_color_override='#0068C9')
    fig2.update_traces(mode='lines')
    fig2.update_traces(line=dict(width=2.5))
    fig2.data[1].name = 'Trendi'
    fig2.data[1].showlegend = True
    fig2.update_layout(dict(yaxis_title='MW'), legend_title="Aikasarja")
    st.plotly_chart(fig2, use_container_width=True)

