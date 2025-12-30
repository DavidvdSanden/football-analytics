from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

from football_analytics.utils import helper, visuals

st.title("Players")

st.subheader("Search")

st.subheader("Attackers")

st.subheader("Midfielders")

st.subheader("Defenders")

st.subheader("Goalkeepers")
