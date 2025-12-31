from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

from football_analytics.utils import supabase


@st.cache_data(show_spinner=True)
def load_table(table_name: str, key_column: str, columns: str = "*") -> pd.DataFrame:
    rows = supabase.fetch_all_rows_in_batches(
        table_name=table_name,
        key_column=key_column,
        columns=columns,
    )
    return pd.DataFrame(rows)


st.title("Club List")
st.write("Loads the clubs table and shows unique club names.")

with st.sidebar:
    table_name = st.text_input("Table name", "teams")
    key_column = st.text_input("Key column", "team_id")

df = load_table(table_name=table_name, key_column=key_column)

if df.empty:
    st.warning("No rows returned from the clubs table.")
else:
    column_candidates = [
        "team_id",
        "team_name",
    ]
    lower_cols = {col.lower(): col for col in df.columns}
    default_col = next(
        (lower_cols[c] for c in column_candidates if c in lower_cols),
        df.columns[0],
    )
    club_column = st.selectbox(
        "Club column",
        options=list(df.columns),
        index=list(df.columns).index(default_col),
    )
    unique_clubs = sorted(df[club_column].dropna().astype(str).unique().tolist())
    st.write(f"Unique clubs: {len(unique_clubs)}")
    st.dataframe(pd.DataFrame({"club": unique_clubs}), use_container_width=True)
