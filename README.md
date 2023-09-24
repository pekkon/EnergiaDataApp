# EnergiaDataApp
EnergiaDataApp is a tool to look into Finnish wind power and other power system data.
App is created using Streamlit and it's hosted here:

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://energiadata.streamlit.app)

The app is using data fetched from Fingrid, ENTSO-E Transparency Platform and Finnish Meteorology Institute (FMI) open data services. 
Due to restrictions on FMI API, older temperature data is pre-downloaded into a csv-file (old_temperatures.csv)
for performance reasons. 

The rest of the data is downloaded from the APIs while using Streamlit's own caching solution to improve performance.

Feel free to contact me on 𝕏, and PRs are also welcome, if you have cool ideas!

[![Twitter URL](https://img.shields.io/twitter/url/https/twitter.com/PekkoNiemi.svg?style=social&label=%20%40PekkoNiemi)](https://twitter.com/PekkoNiemi)

# TODO:
- [ ] Price data: Electricity prices, commodity prices, futures prices?
  - Licensing stuff...
- [x] Launch 🚀
