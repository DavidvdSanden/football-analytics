from pathlib import Path
import sys
from supabase import create_client
import streamlit as st
from football_analytics.utils import helper, visuals
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))


st.set_page_config(
    page_title="Match Data",
    layout="wide"
)
st.title("Match Data")


supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_ANON_KEY"]
)

@st.cache_data(ttl=300)
def load_matches():
    response = (
        supabase
        .table("matches")
        .select("match_id")
        .execute()
    )

    df = pd.DataFrame(response.data)
    return sorted(df["match_id"].unique().tolist())


def load_shot_by_match(match_id: str):
    response = (
        supabase
        .table("shots")
        .select("*")
        .eq("match_id", match_id)
        .execute()
    )
    return response.data

matches = load_matches()

match_id = st.selectbox(
    "Select match ID",
    matches
)

st.write(f"Selected match ID: {match_id}")

shot_data = pd.DataFrame(load_shot_by_match(match_id))

st.dataframe(shot_data[["statsbomb_event_id", "minute", "second", "x1", "y1", "statsbomb_xg", "outcome", "shot_taker_id", "attacking_team_id"]],
             use_container_width=True,)


fig = visuals.plot_shot_overview(shot_data[["statsbomb_event_id", "minute", "second", "x1", "y1", "statsbomb_xg", "outcome", "shot_taker_id", "attacking_team_id"]].to_dict(orient="records"), 
                                 show=False,
                                 xg_column="statsbomb_xg")
st.plotly_chart(fig, use_container_width=True)