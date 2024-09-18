import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objs as go
import plotly
from streamlit_extras.chart_container import chart_container
from src.fingridapi import get_data_from_fg_api_with_start_end, search_fg_api
from src.general_functions import get_general_layout, aggregate_data, sidebar_contact_info
from datetime import datetime, time, timedelta, date

st.set_page_config(
    page_title="EnergiaData - Tuuli- ja sähköjärjestelmätilastoja",
    page_icon="https://i.imgur.com/Kd4P3y2.png",
    layout='wide',
    initial_sidebar_state='expanded'
)


@st.cache_data(show_spinner=False)
def convert_df_to_csv(df):
    return df.to_csv().encode("utf-8")


@st.cache_data(show_spinner=False, max_entries=200)
def get_data_df(start, end, id, nimi):
    """
    Get the production and  demand values from Fingrid API between the start and end dates
    :param start: start date
    :param end: end date
    :return: production dataframe with demand values included
    """
    df = get_data_from_fg_api_with_start_end(id, start, end)
    df.rename({'Value': nimi}, axis=1, inplace=True)
    return df


def click_button():
    st.session_state.clicked = True


def search_button_click():
    st.session_state.search = True


@st.cache_data(show_spinner=False, max_entries=200)
def search_data_df(search_key, api_key):
    search_df = search_fg_api(search_key, api_key)
    search_df = search_df[['nameFi', 'id', 'dataPeriodFi', 'unitFi', 'searchScore', 'descriptionFi']]
    search_df.insert(0, 'search', False)
    return search_df

datahub_mapping = {
    'BE01': 'Asunnot, kerrostalo',
    'BE02': 'Asunnot, pientalo (rivi-, pari- ja omakotitalo), sähkölämmitteinen',
    'BE03': 'Asunnot, pientalo (rivi-, pari- ja omakotitalo), ei-sähkölämmitteinen',
    'BE04': 'Asunnot, vapaa-ajan asunto',
    'BE05': 'Asuinkiinteistöt',
    'BE06': 'Maataloustuotanto (TOL A)',
    'BE07': 'Teollisuus (TOL B ja C)',
    'BE08': 'Yhdyskuntahuolto tai energia- ja vesihuolto (TOL D, E)',
    'BE09': 'Rakentaminen (tilapäissähkö) (TOL F)',
    'BE10': 'Palvelut',
    'BE11': 'Ulkovalaistus',
    'BE12': 'Sähköautojen latauspisteet',
    'BE13': 'Liikenne',
    'BE14': 'Muu kohde',
    'AB01': 'Yritys',
    'AB02': 'Kuluttaja',
    'AV01': 'Vesivoima',
    'AV02': 'Tuulivoima',
    'AV03': 'Ydinvoima',
    'AV04': 'Kaasuturbiini',
    'AV05': 'Diesel-voimakone',
    'AV06': 'Aurinkovoima',
    'AV07': 'Aaltovoima',
    'AV08': 'Yhteistuotanto',
    'AV09': 'Biovoima',
    'AV10': 'Muu tuotanto',
    '0': '0-2000 kWh',
    '2k': '2000-20 000 kWh',
    '20k': '20 000-100 000 kWh',
    '100k': 'yli 100 000 kWh'
}

st.image('./src/EnergiaDashboard.png', width=1000)
with st.sidebar:
    sidebar_contact_info()

if 'clicked' not in st.session_state:
    st.session_state.clicked = False
if 'search' not in st.session_state:
    st.session_state.search = False
if 'fetced' not in st.session_state:
    st.session_state.fetched = False

st.header('Fingridin avoimen datan vapaa haku')
st.write("Työkalun avulla voit hakea itse vapaasti mitä tahansa tietolähdettä Fingridin avoimesta datasta.")

api_key = st.text_input("Anna oma API-avaimesi hakua varten:")
st.markdown(
    "API-avaimen voit hankkia rekisteröitymällä / kirjautumalla [data.fingrid.fi](https://data.fingrid.fi/instructions)  \n"
    "API-avainta ei tallenneta erikseen mihinkään, se pysyy vain selaimen muistissa tallessa.")

with st.expander("Tietolähteiden haku ja valinta"):
    search_key = st.text_input("Anna hakuavain, mitä tietolähdettä etsit:")
    button = st.button("Hae", on_click=click_button)
    if st.session_state.clicked and api_key:
        try:
            search_df = search_data_df(search_key, api_key)
            search_score_max = search_df['searchScore'].max()

        except KeyError as e:
            st.error("Haussa tapahtui virhe, tuloksia ei mahdollisesti löytynyt, voit myös "
                     "yrittää uudestaan tai tarkista API-avain.")
            st.session_state.clicked = False
    elif not api_key:
        st.warning("Aseta API-avain")

    if st.session_state.clicked:
        end = datetime.now()
        st.write("Valitse aikaväli, jolta haluat hakea dataa:")
        col1, col2, _ = st.columns(3)
        with col1:
            start_date = st.date_input("Päivä alkaen", date(2024, 1, 1),
                                       min_value=date(2015, 1, 1),
                                       max_value=end)
        with col2:
            end_date = st.date_input("Päivä saakka", end,
                                     min_value=start_date,
                                     max_value=end)
        st.write("Valitse haluamasi tietolähteet")
        with st.form("data_search"):
            edited_df = st.data_editor(
                search_df,
                column_config={
                    "nameFi": "Nimi",
                    "id": "ID",
                    'dataPeriodFi': "Mittausväli",
                    'unitFi': 'Yksikkö',
                    'searchScore': st.column_config.ProgressColumn(
                        "Haun osumatarkkuus",
                        help="Kuinka hyvin hakuavain vastaa kyseistä tietolähdettä",
                        format="%d",
                        min_value=0,
                        max_value=search_score_max,
                    ),
                    "search": st.column_config.CheckboxColumn(
                        "Hae?",
                        help="Valitse haluamasi tietolähteet",
                        default=False,
                    ),
                    'descriptionFi': "Kuvaus"

                },
                disabled=["nameFi", "id", 'dataPeriodFi', 'unitFi', 'searchScore', 'descriptionFi'],
                hide_index=True,
            )

            search_data = st.form_submit_button("Hae dataa", on_click=search_button_click)
df_list = []
if st.session_state.search:
    st.header("Hakutulokset:")

    for i, row in edited_df[edited_df['search'] == True].iterrows():
        data_id = row['id']
        data_name = row['nameFi']
        data_unit = row['unitFi']
        data_period = row['dataPeriodFi']
        with st.status(f"{data_name}"):
            if (end_date - start_date > timedelta(28)) and data_period == "3 min":
                st.toast(f'Datahaku {data_name} mittausväli on 3 min ja sen haku voi kestää pidempään')
            data = get_data_df(start_date, end_date, data_id, data_name)

            # Handle Datahub data
            if len(data.columns) > 1:
                cols = list(data.columns[1:])
                data = pd.pivot_table(data=data, index=data.index, columns=cols, values=data_name)
                # Flatten multi-index columns
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = [(datahub_mapping[col[0]], datahub_mapping[col[1]]) for col in data.columns]
                    data.columns = [' - '.join(col).strip() for col in data.columns]
                else:
                    data.columns = [datahub_mapping[col] for col in data.columns]

            else:
                df_list.append(data)
            with chart_container(data, ["Kuvaaja 📈", "Data 📄", "Lataa 📁"], ["CSV"]):
                fig = px.line(data)
                fig.update_traces(line=dict(width=2.5))
                fig.update_layout(dict(yaxis_title=data_unit, legend_title="Aikasarja", yaxis_tickformat=".2r",
                                       yaxis_hoverformat=".1f"))
                st.plotly_chart(fig, use_container_width=True)
    st.session_state.fetched = True
if st.session_state.fetched and len(df_list) > 1:
    with st.status("Yhdistetty haut", expanded=True):
        aggregation_selection = st.radio('Valitse datan aggregointitaso',
                                         ['3min', '15min', 'Tunti', 'Päivä', 'Viikko', 'Kuukausi'],
                                         key="search_agg", horizontal=True, index=2)

        all_data = pd.concat(df_list, axis=1)
        all_data = aggregate_data(all_data, aggregation_selection, 'ffill')
        with chart_container(all_data, ["Kuvaaja 📈", "Data 📄", "Lataa 📁"], ["CSV"]):
            fig = px.line(all_data)
            fig.update_traces(line=dict(width=2.5))
            fig.update_layout(dict(yaxis_title="", legend_title="Aikasarja", yaxis_tickformat=".2r",
                                   yaxis_hoverformat=".1f"))
            st.plotly_chart(fig, use_container_width=True)
