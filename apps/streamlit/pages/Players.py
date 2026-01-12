from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

from football_analytics.streamlit.data import (
    load_competitions,
    load_matches,
    load_players,
    load_teams,
)

ICON_PATH = Path(__file__).resolve().parents[1] / "icon_512.png"
st.set_page_config(
    page_title="Football Analysis", page_icon=str(ICON_PATH), layout="wide"
)
st.markdown(
    """
<style>
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 1rem;
}
</style>
""",
    unsafe_allow_html=True,
)
st.title("Players")

st.markdown("### Player Search and Filter")
players = load_players()
if players.empty:
    st.warning("No player data available.")
    st.stop()

players = players.copy()
players["display_label"] = players["player_name"].fillna("Unknown player")
if "team_name" in players.columns:
    players["display_label"] = (
        players["display_label"] + " - " + players["team_name"].fillna("Unknown team")
    )

display_columns = [
    col
    for col in (
        "player_name",
        "team_name",
        "position_name",
        "jersey_number",
        "statsbomb_player_id",
    )
    if col in players.columns
]

tab_search, tab_filters = st.tabs(["Search by name", "Filter by club/season/team"])

with tab_search:
    query = st.text_input(
        "Search player name",
        placeholder="Type a player name",
    )
    filtered = players
    if query.strip():
        filtered = players[
            players["player_name"].str.contains(query, case=False, na=False)
        ]

    if filtered.empty:
        st.info("No players match that search.")
    else:
        options = sorted(filtered["display_label"].dropna().unique().tolist())
        selected_label = st.selectbox("Select a player", options=options)
        selected = filtered[filtered["display_label"] == selected_label]
        st.dataframe(
            selected[display_columns], use_container_width=True, hide_index=True
        )

with tab_filters:
    competitions = load_competitions()
    matches = load_matches()
    teams = load_teams()

    if competitions.empty or matches.empty or teams.empty:
        st.warning("Competition, match, or team data is missing.")
        st.stop()

    competition_options = sorted(
        competitions["competition_name"].dropna().unique().tolist()
    )
    competition = st.selectbox("Competition", options=competition_options)

    seasons = (
        competitions.loc[competitions["competition_name"] == competition, "season_name"]
        .dropna()
        .unique()
        .tolist()
    )
    seasons = sorted(seasons)
    if not seasons:
        st.info("No seasons found for the selected competition.")
        st.stop()

    season = st.selectbox("Season", options=seasons)
    selected_competition_id = competitions.loc[
        competitions["competition_name"] == competition, "competition_id"
    ].iloc[0]
    selected_season_id = competitions.loc[
        (competitions["competition_name"] == competition)
        & (competitions["season_name"] == season),
        "season_id",
    ].iloc[0]

    matches_filtered = matches.loc[
        (matches["competition_id"] == selected_competition_id)
        & (matches["season_id"] == selected_season_id)
    ]
    if matches_filtered.empty:
        st.info("No matches found for the selected competition and season.")
        st.stop()

    team_ids = pd.unique(
        pd.concat([matches_filtered["home_team_id"], matches_filtered["away_team_id"]])
    )
    teams_filtered = teams[teams["team_id"].isin(team_ids)].copy()
    if teams_filtered.empty:
        st.info("No teams found for the selected competition and season.")
        st.stop()

    team_options = sorted(teams_filtered["team_name"].dropna().unique().tolist())
    selected_team = st.selectbox("Team", options=team_options)

    if "team_id" in players.columns:
        teams_filtered["team_id"] = pd.to_numeric(
            teams_filtered["team_id"], errors="coerce"
        )
        players["team_id"] = pd.to_numeric(players["team_id"], errors="coerce")
        team_id = teams_filtered.loc[
            teams_filtered["team_name"] == selected_team, "team_id"
        ].iloc[0]
        team_players = players[players["team_id"] == team_id]
    elif "team_name" in players.columns:
        team_players = players[players["team_name"] == selected_team]
    else:
        st.warning("Player team data is missing; cannot filter by team.")
        st.stop()

    if team_players.empty:
        st.info("No players found for the selected team.")
    else:
        options = sorted(team_players["display_label"].dropna().unique().tolist())
        selected_label = st.selectbox("Select a player", options=options)
        selected = team_players[team_players["display_label"] == selected_label]
        st.dataframe(
            selected[display_columns], use_container_width=True, hide_index=True
        )

st.markdown("---")
