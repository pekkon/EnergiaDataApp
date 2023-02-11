import streamlit as st
from streamlit_extras.buy_me_a_coffee import button
from streamlit_extras.mention import mention

import datetime



def get_general_layout(start=datetime.date(2023, 1, 1)):
    # Start of the page
    st.title('EnergiaData (tämä kuvana)')
    st.image('https://i.imgur.com/AzAQTPr.png', width=300)
    curr_date = datetime.datetime.now()
    st.sidebar.subheader("Valitse aikaikkuna 📆")
    st.session_state['start_date_max_value'] = curr_date
    # Setup date inputs so user can select their desired date range but make sure they don't non-feasible date ranges
    # start_date cannot go over end_date, and we need to save end_date to session_state in case user changed end_date

    start_date = st.sidebar.date_input("Päivä alkaen", start, min_value=datetime.date(2015, 1, 1),
                                       max_value=st.session_state['start_date_max_value'])
    end_date = st.sidebar.date_input("Päivä saakka", curr_date, min_value=start_date, max_value=curr_date)
    st.session_state['start_date_max_value'] = end_date
    st.session_state['end_date_selected'] = curr_date

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
        label="EnergiaBotti",
        icon="twitter",
        url="https://twitter.com/EnergiaBotti"
    )

    mention(
        label="EnergiaData-sovelluksen lähdekoodi",
        icon="github",
        url="https://github.com/pekkon/EnergiaDataApp"
    )
    st.markdown('Datalähteenä [Fingridin avoin data](https://data.fingrid.fi)')
    button("pekko", False, "Buy me a pizza", "🍕", width=250)


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


