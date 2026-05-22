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
        section_heading,
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
    section_heading = module.section_heading
from football_analytics.streamlit.data import (
    load_competitions,
    load_matches,
    load_players,
    load_teams,
)

ICON_PATH = Path(__file__).resolve().parents[2] / "icon_512.png"
st.set_page_config(
    page_title="Football Analysis", page_icon=str(ICON_PATH), layout="wide"
)
inject_sidebar_navigation_brand(ICON_PATH)
page_header(
    "Players",
    "Search by name or filter by competition, season, and team.",
)
section_heading("Player Search and Filter")
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
    top_left_col, top_right_col = st.columns(2, gap="small")
    with top_left_col:
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

    with top_right_col:
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
    bottom_left_col, bottom_right_col = st.columns(2, gap="small")
    with bottom_left_col:
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
        with bottom_right_col:
            selected_label = st.selectbox("Select a player", options=options)
        selected = team_players[team_players["display_label"] == selected_label]
        st.dataframe(
            selected[display_columns], use_container_width=True, hide_index=True
        )
