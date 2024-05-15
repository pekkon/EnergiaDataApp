import streamlit as st
from src.general_functions import get_general_layout

st.set_page_config(
    page_title="EnergiaData - Tuuli- ja sähköjärjestelmätilastoja",
    page_icon="https://i.imgur.com/Kd4P3y2.png",
    layout='wide',
    initial_sidebar_state='expanded'
)

get_general_layout()

st.markdown(f"EnergiaDashboard on työkalu, jolla voit tutustua Suomen sähköjärjestelmän tilastotietoon. Se "
            f"hyödyntää lähinnä Fingridin avointa dataa. Dataa voi hakea 2018 alusta alkaen ja mitä enemmän dataa "
            f"haet kerralla, sitä pidempään kuvaajien päivittyminen kestää.   \n\n"
            f"Työkalu on koodattu Streamlit-nimisen kirjaston avulla. "
            f"Ongelmatilanteissa kannattaa ensin yrittää painaa näppäimistön 'R'-painiketta tai valita oikeasta "
            f"yläkulmasta löytyvän valikon kautta 'Rerun'. Ongelmien jatkuessa voit olla yhteydessä erikseen.  \n\n"
            f"")
