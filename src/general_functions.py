import streamlit as st
from streamlit_extras.mention import mention

import datetime



def get_general_layout(start=None):
    # Start of the page
    end = datetime.datetime.now()
    st.image('./src/EnergiaDashboard.png', width=1000)
    st.sidebar.subheader("Valitse aikaikkuna 📆")
    if start is not None:
        default = datetime.date(2018, 1, 1)
    else:
        if 'current_start_date' in st.session_state:
            default = st.session_state['current_start_date']
        else:
            default = datetime.date(2023, 1, 1)

    # Setup date inputs so user can select their desired date range but make sure they don't non-feasible date ranges
    # start_date cannot go over end_date, and we need to save end_date to session_state in case user changed end_date

    if 'current_end_date' not in st.session_state:
        start_date = st.sidebar.date_input("Päivä alkaen", default,
                                           min_value=datetime.date(2015, 1, 1),
                                           max_value=end)
        end_date = st.sidebar.date_input("Päivä saakka", end,
                                         min_value=start_date,
                                         max_value=end, key='current_end_date')
    else:
        start_date = st.sidebar.date_input("Päivä alkaen", default,
                                           min_value=datetime.date(2015, 1, 1),
                                           max_value=st.session_state['current_end_date'])
        end_date = st.sidebar.date_input("Päivä saakka", st.session_state['current_end_date'],
                                         min_value=start_date,
                                         max_value=end, key='current_end_date')
    if start is None:
        st.session_state['current_start_date'] = start_date
    aggregation_selection = st.sidebar.radio('Valitse aggregointitaso 🕑', ['Tunti', 'Päivä', 'Viikko', 'Kuukausi'])

    # Add contact info and other information to the end of sidebar
    with st.sidebar:
        sidebar_contact_info()

    return start_date, end_date, aggregation_selection


def sidebar_contact_info():
    # Setup sidebar contact and other info

    st.subheader("Ota yhteyttä:")
    mention(
        label="Pekko Niemi",
        icon="twitter",
        url="https://twitter.com/PekkoNiemi"
    )
    mention(
        label="EnergiaData-sovelluksen lähdekoodi",
        icon="github",
        url="https://github.com/pekkon/EnergiaDataApp"
    )
    st.markdown('Datalähteenä [Fingridin avoin data](https://data.fingrid.fi)')


@st.cache_data(show_spinner=False, max_entries=200)
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
    return df.resample(agg).mean().round(1)


