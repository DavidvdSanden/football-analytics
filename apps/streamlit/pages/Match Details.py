from pathlib import Path
import sys
from football_analytics.visuals import shots
from supabase import create_client
import streamlit as st
from football_analytics.utils import helper
import pandas as pd
from football_analytics.streamlit.components import match_header
from football_analytics.streamlit.data import (
    load_competitions,
    load_teams,
    load_matches,
    load_shot_by_match,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))


st.set_page_config(page_title="Match Data", layout="wide")
st.title("Match Details")

competitions = load_competitions()
teams = load_teams()
matches = load_matches()

# -------------------
### Match Selection ###
# -------------------
st.sidebar.subheader("Match Selection")
# --- Competition ---
competition = st.sidebar.selectbox(
    "Competition", sorted(competitions["competition_name"].dropna().unique())
)
selected_competition_id = competitions.loc[
    competitions["competition_name"] == competition, "competition_id"
].unique()[0]

# --- Season ---
seasons = sorted(
    competitions.loc[competitions["competition_name"] == competition, "season_name"]
    .dropna()
    .unique()
)
season = st.sidebar.selectbox("Season", seasons)
selected_season_id = competitions.loc[
    (competitions["competition_name"] == competition)
    & (competitions["season_name"] == season),
    "season_id",
].unique()[0]


# --- Match ---
comp_season_ids = competitions.loc[
    (competitions["competition_name"] == competition)
    & (competitions["season_name"] == season),
    "competition_id",
].unique()

matches_filtered = matches.loc[
    (matches["competition_id"] == selected_competition_id)
    & (matches["season_id"] == selected_season_id)
].copy()

if matches_filtered.empty:
    st.sidebar.selectbox("Match", ["No matches available"])
    st.info("No matches available for the selected competition and season.")
    st.stop()

matches_with_names = matches_filtered.merge(
    teams.rename(columns={"team_id": "home_team_id", "team_name": "home_team_name"}),
    on="home_team_id",
    how="left",
).merge(
    teams.rename(columns={"team_id": "away_team_id", "team_name": "away_team_name"}),
    on="away_team_id",
    how="left",
)

matches_with_names["match_label"] = (
    matches_with_names["home_team_name"].fillna("Unknown")
    + " vs "
    + matches_with_names["away_team_name"].fillna("Unknown")
    + " ("
    + matches_with_names["match_date"].fillna("Unknown date").astype(str)
    + ")"
)

matches_with_names = matches_with_names.sort_values(by="match_date", ascending=False)

match_label = st.sidebar.selectbox("Match", matches_with_names["match_label"].tolist())

match_id = matches_with_names.loc[
    matches_with_names["match_label"] == match_label, "match_id"
].iloc[0]

selected_match_df = matches[matches["match_id"] == match_id]

st.subheader("Match Statistics")
home_team = teams[teams["team_id"] == selected_match_df["home_team_id"].values[0]][
    "team_name"
].values[0]
away_team = teams[teams["team_id"] == selected_match_df["away_team_id"].values[0]][
    "team_name"
].values[0]

st.markdown("#### Scoreline")
match_header(
    home_team,
    away_team,
    int(selected_match_df["home_score"].values),
    int(selected_match_df["away_score"].values),
)

shot_data = pd.DataFrame(load_shot_by_match(match_id))

st.markdown("#### xG Progression")
fig = shots.plot_xg_progression(
    shots=shot_data,
    home_team_id=selected_match_df["home_team_id"].values[0],
    away_team_id=selected_match_df["away_team_id"].values[0],
    show=False,
    home_team_name=home_team,
    away_team_name=away_team,
)
st.plotly_chart(fig, use_container_width=True)


st.markdown("#### Shot Overview")
fig = shots.plot_shot_overview(
    shot_data[
        [
            "statsbomb_event_id",
            "minute",
            "second",
            "x1",
            "y1",
            "statsbomb_xg",
            "outcome",
            "shot_taker_id",
            "attacking_team_id",
        ]
    ].to_dict(orient="records"),
    show=False,
    xg_column="statsbomb_xg",
    away_on_left=True,
    home_team_id=selected_match_df["home_team_id"].values[0],
    away_team_id=selected_match_df["away_team_id"].values[0],
    pitch_theme="transparent",
    show_axis_labels=False,
)
st.plotly_chart(fig, use_container_width=True)
