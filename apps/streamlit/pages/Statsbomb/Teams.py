from pathlib import Path
import importlib
import importlib.util
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
package_root = str(SRC_PATH / "football_analytics")
loaded_pkg = sys.modules.get("football_analytics")
if loaded_pkg is not None and hasattr(loaded_pkg, "__path__"):
    pkg_paths = [str(p) for p in loaded_pkg.__path__]
    if package_root not in pkg_paths:
        loaded_pkg.__path__.append(package_root)
importlib.invalidate_caches()

try:
    from football_analytics.streamlit.theme import (
        inject_sidebar_navigation_brand,
        page_header,
    )
except ModuleNotFoundError:
    theme_path = SRC_PATH / "football_analytics" / "streamlit" / "theme.py"
    spec = importlib.util.spec_from_file_location(
        "football_analytics.streamlit.theme", theme_path
    )
    if spec is None or spec.loader is None:
        raise
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    inject_sidebar_navigation_brand = module.inject_sidebar_navigation_brand
    page_header = module.page_header
from football_analytics.utils import database

ICON_PATH = Path(__file__).resolve().parents[2] / "icon_512.png"
st.set_page_config(
    page_title="Football Analysis", page_icon=str(ICON_PATH), layout="wide"
)
inject_sidebar_navigation_brand(ICON_PATH)


@st.cache_data(show_spinner=True)
def load_table(table_name: str, key_column: str, columns: str = "*") -> pd.DataFrame:
    rows = database.fetch_all_rows_in_batches(
        table_name=table_name,
        key_column=key_column,
        columns=columns,
    )
    return pd.DataFrame(rows)


page_header(
    "Club List",
    "Browse unique club names from the teams table in the database.",
    content_max_width_px=1320,
)

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
