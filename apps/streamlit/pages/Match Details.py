from pathlib import Path
import sys
from football_analytics.visuals import shots
import streamlit as st
import pandas as pd
from football_analytics.streamlit.components import (
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
ICON_PATH = Path(__file__).resolve().parents[1] / "icon_512.png"
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))


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
h1 {
    margin-bottom: 0.4rem;
}
h2 {
    margin-top: 0.4rem;
}
h3 {
    margin-top: 0.2rem;
}
.section-title {
    margin-top: 0.1rem;
    margin-bottom: 0.5rem;
}
.card {
    border: 1px solid rgba(100,100,100,0.15);
    border-radius: 12px;
    padding: 1rem;
    background: rgba(200,200,200,0.02);
    box-shadow: 0 1px 6px rgba(0,0,0,0.08);
}
.stat-card {
    min-height: 220px;
    height: 220px;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
}
.stat-title {
    font-size: 1.02rem;
    font-weight: 700;
    margin-bottom: 0.55rem;
    line-height: 1.2;
}
.stat-primary {
    font-size: 1.45rem;
    font-weight: 800;
    line-height: 1.1;
    margin-bottom: 0.25rem;
}
.score-card {
    justify-content: flex-start;
    align-items: stretch;
    text-align: left;
}
.score-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}
.scoreline-big {
    font-size: 4.2rem;
    font-weight: 800;
    line-height: 0.95;
    margin: 0;
    text-align: center;
    width: 100%;
}
.score-sub {
    text-align: center;
    margin-top: 0.35rem;
}
.stat-secondary {
    font-size: 0.9rem;
    opacity: 0.85;
}
.stat-table-wrap {
    flex: 1;
    display: flex;
    align-items: center;
}
.stat-grid {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.95rem;
}
.stat-grid th,
.stat-grid td {
    padding: 0.2rem 0.35rem;
    text-align: center;
    border-bottom: 1px solid rgba(100, 100, 100, 0.12);
}
.stat-grid th {
    font-size: 0.8rem;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}
.stat-grid th:first-child,
.stat-grid td:first-child {
    text-align: left;
}
.stat-grid td:first-child {
    font-weight: 400;
}
.stat-grid tbody tr:first-child td {
    font-size: 1rem;
    font-weight: 400;
}
.match-info {
    display: grid;
    grid-template-columns: repeat(3, minmax(140px, 1fr));
    gap: 0.4rem 0.8rem;
    font-size: 0.92rem;
}
.match-info div {
    line-height: 1.25;
}
</style>
""",
    unsafe_allow_html=True,
)
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
home_team_id = int(selected_match_df["home_team_id"].values[0])
away_team_id = int(selected_match_df["away_team_id"].values[0])
home_score = int(selected_match_df["home_score"].values[0])
away_score = int(selected_match_df["away_score"].values[0])
home_team = teams.loc[teams["team_id"] == home_team_id, "team_name"].values[0]
away_team = teams.loc[teams["team_id"] == away_team_id, "team_name"].values[0]
if "match_date" in selected_match_df.columns:
    match_date_raw = selected_match_df["match_date"].iloc[0]
    match_date = str(match_date_raw) if pd.notna(match_date_raw) else "Unknown"
else:
    match_date = "Unknown"

shot_data = pd.DataFrame(load_shot_by_match(match_id))
players = load_players()
if not shot_data.empty and not players.empty and not teams.empty:
    shot_data = shot_data.copy()
    players = players.copy()
    shot_data["attacking_team_id"] = pd.to_numeric(
        shot_data["attacking_team_id"], errors="coerce"
    )
    shot_data["minute"] = pd.to_numeric(shot_data["minute"], errors="coerce")
    shot_data["second"] = pd.to_numeric(shot_data["second"], errors="coerce")
    if "statsbomb_xg" in shot_data.columns:
        shot_data["statsbomb_xg"] = pd.to_numeric(
            shot_data["statsbomb_xg"], errors="coerce"
        )
    shot_data["shot_taker_id"] = pd.to_numeric(
        shot_data["shot_taker_id"], errors="coerce"
    )
    players["statsbomb_player_id"] = pd.to_numeric(
        players["statsbomb_player_id"], errors="coerce"
    )
    player_columns = [
        col
        for col in players.columns
        if col == "statsbomb_player_id"
        or (col not in shot_data.columns and col not in ("team_id", "team_name"))
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

### -------------------
### Match statistics
### -------------------

home_shots = shot_data[shot_data["attacking_team_id"] == home_team_id].copy()
away_shots = shot_data[shot_data["attacking_team_id"] == away_team_id].copy()

home_total_shots = len(home_shots)
away_total_shots = len(away_shots)

home_goals = (
    home_shots["outcome"].astype(str).str.contains("goal", case=False, na=False).sum()
    if "outcome" in home_shots.columns
    else 0
)
away_goals = (
    away_shots["outcome"].astype(str).str.contains("goal", case=False, na=False).sum()
    if "outcome" in away_shots.columns
    else 0
)

on_target_pattern = r"goal|saved"
home_on_target = (
    home_shots["outcome"]
    .astype(str)
    .str.contains(on_target_pattern, case=False, na=False, regex=True)
    .sum()
    if "outcome" in home_shots.columns
    else 0
)
away_on_target = (
    away_shots["outcome"]
    .astype(str)
    .str.contains(on_target_pattern, case=False, na=False, regex=True)
    .sum()
    if "outcome" in away_shots.columns
    else 0
)

home_xg = (
    float(home_shots[xg_column].fillna(0).sum())
    if xg_column in home_shots.columns
    else 0.0
)
away_xg = (
    float(away_shots[xg_column].fillna(0).sum())
    if xg_column in away_shots.columns
    else 0.0
)

home_xg_per_shot = home_xg / home_total_shots if home_total_shots else 0.0
away_xg_per_shot = away_xg / away_total_shots if away_total_shots else 0.0
home_xg_delta = home_xg - away_xg
away_xg_delta = away_xg - home_xg

st.markdown("#### Match Info")
st.markdown(
    f"""
    <div class="card" style="margin-bottom: 0.75rem;">
        <div class="match-info">
            <div><strong>Competition:</strong><br>{competition}</div>
            <div><strong>Season:</strong><br>{season}</div>
            <div><strong>Date:</strong><br>{match_date}</div>
            <div><strong>Home Team:</strong><br>{home_team}</div>
            <div><strong>Away Team:</strong><br>{away_team}</div>
            <div><strong>Scoreline:</strong><br>{home_score} - {away_score}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<h3 class="section-title">Match Statistics</h3>', unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        f"""
        <div class="card stat-card score-card">
            <div class="stat-title">Scoreline</div>
            <div class="score-body">
                <div class="scoreline-big">{home_score} - {away_score}</div>
                <div class="stat-secondary score-sub">{home_team} vs {away_team}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f"""
        <div class="card stat-card">
            <div class="stat-title">Shooting Volume</div>
            <div class="stat-table-wrap">
                <table class="stat-grid">
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>{home_team}</th>
                            <th>{away_team}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Shots</td>
                            <td>{home_total_shots}</td>
                            <td>{away_total_shots}</td>
                        </tr>
                        <tr>
                            <td>On Target</td>
                            <td>{home_on_target}</td>
                            <td>{away_on_target}</td>
                        </tr>
                        <tr>
                            <td>Goals (shots)</td>
                            <td>{home_goals}</td>
                            <td>{away_goals}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        f"""
        <div class="card stat-card">
            <div class="stat-title">xG Quality ({xg_label})</div>
            <div class="stat-table-wrap">
                <table class="stat-grid">
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>{home_team}</th>
                            <th>{away_team}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>xG</td>
                            <td>{home_xg:.2f}</td>
                            <td>{away_xg:.2f}</td>
                        </tr>
                        <tr>
                            <td>xG per Shot</td>
                            <td>{home_xg_per_shot:.3f}</td>
                            <td>{away_xg_per_shot:.3f}</td>
                        </tr>
                        <tr>
                            <td>xG Delta</td>
                            <td>{home_xg_delta:+.2f}</td>
                            <td>{away_xg_delta:+.2f}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

st.markdown(f"#### xG Progression ({xg_label})")
fig = shots.plot_xg_progression(
    shots=shot_data,
    home_team_id=home_team_id,
    away_team_id=away_team_id,
    show=False,
    home_team_name=home_team,
    away_team_name=away_team,
    xg_col=xg_column,
    height_figure=250,
)
fig.update_layout(dragmode="zoom")
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

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


available_shot_columns = [
    col for col in shot_overview_columns if col in shot_data.columns
]
if len(available_shot_columns) != len(shot_overview_columns):
    missing = sorted(set(shot_overview_columns) - set(available_shot_columns))
    if missing:
        st.info(
            "Some shot metadata is unavailable for the overview: " + ", ".join(missing)
        )

st.session_state.setdefault("shot_selected", None)
pitch_height = 520
pitch_margin = dict(l=0, r=0, t=0, b=10)
pitch_y_domain = [0.05, 1]

fig = shots.plot_shot_overview(
    shot_data[available_shot_columns].to_dict(orient="records"),
    show=False,
    xg_column=xg_column,
    away_on_left=True,
    home_team_id=home_team_id,
    away_team_id=away_team_id,
    pitch_theme="transparent",
    show_axis_labels=False,
    pitch_padding=0,
    layout_margin=pitch_margin,
    fixed_size=False,
)
fig.update_layout(
    height=pitch_height,
    margin=pitch_margin,
    autosize=True,
    margin_autoexpand=False,
)
fig.update_layout(dragmode="zoom")
fig.update_yaxes(domain=pitch_y_domain)

columns = st.columns(2)
with columns[0]:
    event = st.plotly_chart(
        fig,
        use_container_width=True,
        key="shot_overview",
        on_select="rerun",
        selection_mode=("points",),
        config={"responsive": True, "displayModeBar": False},
    )
    selection = event.selection if event else None
    point_indices = selection.get("point_indices") if selection else None
    st.session_state.shot_selected = int(point_indices[0]) if point_indices else None

shot_index = st.session_state.shot_selected
with columns[1]:
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
            home_team_id=home_team_id,
            away_team_id=away_team_id,
        )
        fig.update_layout(
            height=pitch_height,
            margin=pitch_margin,
            autosize=True,
            margin_autoexpand=False,
        )
        fig.update_layout(dragmode="zoom")
        fig.update_yaxes(domain=pitch_y_domain)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    elif shot_index is not None and 0 <= shot_index < len(shot_data):
        selected_shot_data = shot_data.iloc[shot_index]
        raw_full_json = selected_shot_data["full_json"]
        if isinstance(raw_full_json, (str, bytes, bytearray)):
            shot_payload = json.loads(raw_full_json)
        else:
            shot_payload = raw_full_json
        fig = shots.plot_shot_details(
            shot_payload,
            show=False,
            show_axis_labels=False,
            pitch_theme="transparent",
            fixed_size=False,
            pitch_padding=0,
            away_on_left=True,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
        )
        fig.update_layout(
            height=pitch_height,
            margin=pitch_margin,
            autosize=True,
            margin_autoexpand=False,
        )
        fig.update_layout(dragmode="zoom")
        fig.update_yaxes(domain=pitch_y_domain)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.warning("Selected shot index is out of range.")

st.markdown("---")
