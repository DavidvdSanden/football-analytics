from pathlib import Path

import streamlit as st

ICON_PATH = Path(__file__).resolve().parents[1] / "icon_512.png"
st.set_page_config(
    page_title="Football Analysis", page_icon=str(ICON_PATH), layout="wide"
)

st.title("Transfermarkt Transfers")
st.info("Starter page for transfer history, move tracking, and squad changes.")
st.write("Add transfer windows, fee summaries, and player movement views here.")
