from pathlib import Path

import streamlit as st

ICON_PATH = Path(__file__).resolve().parents[1] / "icon_512.png"
st.set_page_config(
    page_title="Football Analysis", page_icon=str(ICON_PATH), layout="wide"
)

st.title("Transfermarkt Players")
st.info(
    "Starter page for Transfermarkt player profiles, market values, and scouting data."
)
st.write(
    "Add Transfermarkt player tables and filters here when the data pipeline is ready."
)
