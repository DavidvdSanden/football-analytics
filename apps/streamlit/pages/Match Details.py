from pathlib import Path
import sys
from supabase import create_client
import streamlit as st
from football_analytics.utils import helper, visuals
import pandas as pd
import textwrap


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))


st.set_page_config(page_title="Match Data", layout="wide")
st.title("Match Details")


supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])

# -------------------
### Helper Functions ###
# -------------------


@st.cache_data(ttl=300)
def load_competitions():
    response = (
        supabase.table("competitions")
        .select("competition_id, competition_name, season_name, season_id")
        .execute()
    )
    df = pd.DataFrame(response.data)
    return df


@st.cache_data(ttl=300)
def load_teams():
    response = supabase.table("teams").select("team_id, team_name").execute()
    df = pd.DataFrame(response.data)
    return df


@st.cache_data(ttl=300)
def load_matches():
    response = (
        supabase.table("matches")
        .select(
            "match_id, home_team_id, away_team_id, home_score, away_score, match_date, competition_id, season_id"
        )
        .execute()
    )
    df = pd.DataFrame(response.data)
    return df


@st.cache_data(ttl=300)
def load_shot_by_match(match_id: str):
    response = supabase.table("shots").select("*").eq("match_id", match_id).execute()
    return response.data


def match_header(home_team, away_team, home_goals, away_goals):
    html = f"""
        <div style="width:100%; text-align:center;">
            <!-- Team names -->
            <div style="
                display: grid;
                grid-template-columns: 1fr auto 1fr;
                align-items: center;
                font-size: 22px;
                font-weight: 600;
                margin-bottom: 0.25rem;
            ">
                <div style="text-align: right; padding-right: 0.5rem;">{home_team}</div>
                <div style="opacity: 0.6; text-align: center;">–</div>
                <div style="text-align: left; padding-left: 0.5rem;">{away_team}</div>
            </div>
            <!-- Score -->
            <div style="
                display: grid;
                grid-template-columns: 1fr auto 1fr;
                align-items: center;
                font-size: 80px;
                font-weight: 800;
                line-height: 1;
            ">
                <div style="text-align: right; padding-right: 0.5rem;">{home_goals}</div>
                <div style="opacity: 0.6; text-align: center;">–</div>
                <div style="text-align: left; padding-left: 0.5rem;">{away_goals}</div>
            </div>
        </div>
        """
    st.markdown(textwrap.dedent(html), unsafe_allow_html=True)


competitions = load_competitions()
teams = load_teams()
matches = load_matches()

# -------------------
### Match Selection ###
# -------------------
st.subheader("Match Selection")
# --- Competition ---
competition = st.selectbox(
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
season = st.selectbox("Season", seasons)
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
    st.selectbox("Match", ["No matches available"])
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

match_label = st.selectbox("Match", matches_with_names["match_label"].tolist())

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
fig = visuals.plot_xg_progression(
    shots=shot_data,
    home_team_id=selected_match_df["home_team_id"].values[0],
    away_team_id=selected_match_df["away_team_id"].values[0],
    show=False,
    home_team_name=home_team,
    away_team_name=away_team,
)
st.plotly_chart(fig, use_container_width=True)


st.markdown("#### Shot Overview")
fig = visuals.plot_shot_overview(
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
