from pathlib import Path
import sys
from football_analytics.visuals import shots
import streamlit as st
import pandas as pd
from football_analytics.streamlit.components import (
    match_header,
    enable_plotly_auto_resize,
)
from football_analytics.streamlit.data import (
    load_competitions,
    load_teams,
    load_matches,
    load_players,
    load_shot_by_match,
)
from football_analytics.streamlit.xg import apply_xg_model_selection
import json


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))


st.set_page_config(page_title="Match Data", layout="wide")
st.title("Match Details")
enable_plotly_auto_resize()

competitions = load_competitions()
teams = load_teams()
matches = load_matches()

# -------------------
### Match Selection ###
# -------------------
st.sidebar.subheader("Match Selection")
# --- Competition ---
competition_options = sorted(competitions["competition_name"].dropna().unique())
stored_competition_id = st.session_state.get("selected_competition_id")
if stored_competition_id is not None:
    stored_competition_name = competitions.loc[
        competitions["competition_id"] == stored_competition_id, "competition_name"
    ]
    default_competition = (
        stored_competition_name.iloc[0]
        if not stored_competition_name.empty
        else competition_options[0]
    )
else:
    default_competition = competition_options[0]
competition_index = (
    competition_options.index(default_competition)
    if default_competition in competition_options
    else 0
)
competition = st.sidebar.selectbox(
    "Competition", competition_options, index=competition_index, key="competition"
)
selected_competition_id = competitions.loc[
    competitions["competition_name"] == competition, "competition_id"
].unique()[0]
st.session_state["selected_competition_id"] = selected_competition_id

# --- Season ---
seasons = sorted(
    competitions.loc[competitions["competition_name"] == competition, "season_name"]
    .dropna()
    .unique()
)
stored_season_id = st.session_state.get("selected_season_id")
if stored_season_id is not None:
    stored_season_name = competitions.loc[
        competitions["season_id"] == stored_season_id, "season_name"
    ]
    default_season = (
        stored_season_name.iloc[0] if not stored_season_name.empty else seasons[0]
    )
else:
    default_season = seasons[0]
season_index = seasons.index(default_season) if default_season in seasons else 0
season = st.sidebar.selectbox("Season", seasons, index=season_index, key="season")
selected_season_id = competitions.loc[
    (competitions["competition_name"] == competition)
    & (competitions["season_name"] == season),
    "season_id",
].unique()[0]
st.session_state["selected_season_id"] = selected_season_id

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
    matches_with_names["match_date"].fillna("Unknown date").astype(str)
    + " – "
    + matches_with_names["home_team_name"].fillna("Unknown")
    + " vs "
    + matches_with_names["away_team_name"].fillna("Unknown")
)

matches_with_names = matches_with_names.sort_values(by="match_date", ascending=False)

match_labels = matches_with_names["match_label"].tolist()
stored_match_id = st.session_state.get("selected_match_id")
if (
    stored_match_id is not None
    and stored_match_id in matches_with_names["match_id"].values
):
    stored_match_label = matches_with_names.loc[
        matches_with_names["match_id"] == stored_match_id, "match_label"
    ].iloc[0]
    match_index = match_labels.index(stored_match_label)
else:
    match_index = 0
match_label = st.sidebar.selectbox(
    "Match", match_labels, index=match_index, key="match"
)

match_id = matches_with_names.loc[
    matches_with_names["match_label"] == match_label, "match_id"
].iloc[0]
st.session_state["selected_match_id"] = match_id

selected_match_df = matches[matches["match_id"] == match_id]

### -------------------
### Match statistics
### -------------------

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
players = load_players()
if not shot_data.empty and not players.empty and not teams.empty:
    shot_data = shot_data.copy()
    players = players.copy()
    shot_data["shot_taker_id"] = pd.to_numeric(
        shot_data["shot_taker_id"], errors="coerce"
    )
    players["statsbomb_player_id"] = pd.to_numeric(
        players["statsbomb_player_id"], errors="coerce"
    )
    player_columns = [
        col
        for col in players.columns
        if col == "statsbomb_player_id" or col not in shot_data.columns
    ]
    shot_data = shot_data.merge(
        players[player_columns],
        left_on="shot_taker_id",
        right_on="statsbomb_player_id",
        how="left",
    )

    teams["team_id"] = pd.to_numeric(teams["team_id"], errors="coerce")
    shot_data = shot_data.merge(
        teams[["team_id", "team_gender", "team_name"]],
        left_on="attacking_team_id",
        right_on="team_id",
        how="left",
    )
    shot_data["is_male"] = shot_data["team_gender"].apply(
        lambda x: 1 if x == "male" else 0
    )

shot_data, xg_column, xg_label = apply_xg_model_selection(
    shot_data, model_dir=PROJECT_ROOT / "models" / "xg_model" / "nn_models"
)

st.markdown(f"#### xG Progression ({xg_label})")
fig = shots.plot_xg_progression(
    shots=shot_data,
    home_team_id=selected_match_df["home_team_id"].values[0],
    away_team_id=selected_match_df["away_team_id"].values[0],
    show=False,
    home_team_name=home_team,
    away_team_name=away_team,
    xg_col=xg_column,
)
st.plotly_chart(fig, use_container_width=True)

### -------------------
### Shot Overview
### -------------------

st.markdown(f"#### Shot Overview ({xg_label})")
shot_overview_columns = [
    "statsbomb_event_id",
    "minute",
    "second",
    "x1",
    "y1",
    "outcome",
    "shot_taker_id",
    "attacking_team_id",
    "player_name",
    "team_name",
]
if xg_column not in shot_overview_columns:
    shot_overview_columns.insert(5, xg_column)


st.session_state.setdefault("shot_selected", None)
pitch_height = 440
pitch_margin = dict(l=0, r=0, t=0, b=0)

fig = shots.plot_shot_overview(
    shot_data[shot_overview_columns].to_dict(orient="records"),
    show=False,
    xg_column=xg_column,
    away_on_left=True,
    home_team_id=selected_match_df["home_team_id"].values[0],
    away_team_id=selected_match_df["away_team_id"].values[0],
    pitch_theme="transparent",
    show_axis_labels=False,
    pitch_padding=0,
    layout_margin=pitch_margin,
    fixed_size=False,
)
fig.update_layout(height=pitch_height, margin=pitch_margin, autosize=True)

event = st.plotly_chart(
    fig,
    use_container_width=True,
    key="shot_overview",
    on_select="rerun",
    selection_mode=("points",),
    config={"responsive": True},
)
selection = event.selection if event else None
point_indices = selection.get("point_indices") if selection else None
st.session_state.shot_selected = int(point_indices[0]) if point_indices else None


shot_index = st.session_state.shot_selected
if shot_index is None:
    # Creating empty dict to plot an empty pitch
    empty_dict = {}
    fig = shots.plot_shot_details(
        empty_dict,
        show=False,
        show_axis_labels=False,
        pitch_theme="transparent",
        fixed_size=False,
        pitch_padding=0,
        away_on_left=True,
        home_team_id=selected_match_df["home_team_id"].values[0],
        away_team_id=selected_match_df["away_team_id"].values[0],
    )
    fig.update_layout(height=pitch_height, margin=pitch_margin, autosize=True)
    st.plotly_chart(fig, use_container_width=True)

elif shot_index is not None and 0 <= shot_index < len(shot_data):
    selected_shot_data = shot_data.iloc[shot_index]
    fig = shots.plot_shot_details(
        json.loads(selected_shot_data["full_json"]),
        show=False,
        show_axis_labels=False,
        pitch_theme="transparent",
        fixed_size=False,
        pitch_padding=0,
        away_on_left=True,
        home_team_id=selected_match_df["home_team_id"].values[0],
        away_team_id=selected_match_df["away_team_id"].values[0],
    )
    fig.update_layout(height=pitch_height, margin=pitch_margin, autosize=True)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Selected shot index is out of range.")
