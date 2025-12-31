from pathlib import Path
import sys
from football_analytics.visuals import shots
import streamlit as st
from football_analytics.utils import helper

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

st.title("Players")

st.subheader("Search")

st.subheader("Attackers")

st.subheader("Midfielders")

st.subheader("Defenders")

st.subheader("Goalkeepers")
