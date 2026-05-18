from pathlib import Path

import streamlit as st

ICON_PATH = Path(__file__).resolve().parents[1] / "icon_512.png"
st.set_page_config(
    page_title="Football Analysis", page_icon=str(ICON_PATH), layout="wide"
)

st.title("Transfermarkt Values")
st.info("Starter page for squad values, player valuations, and market trends.")
st.write("Add valuation history, comparisons, and club-level value summaries here.")
