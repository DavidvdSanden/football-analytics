import pandas as pd
import streamlit as st
from football_analytics.utils import database

# -------------------
### Helper Functions ###
# -------------------


@st.cache_data(ttl=300)
def load_competitions():
    rows = database.fetch_rows(
        table_name="competitions",
        columns="competition_id, competition_name, season_name, season_id",
    )
    df = pd.DataFrame(rows)
    return df


@st.cache_data(ttl=300)
def load_teams():
    rows = database.fetch_rows(
        table_name="teams",
        columns="team_id, team_name, team_gender",
    )
    df = pd.DataFrame(rows)
    return df


@st.cache_data(ttl=300)
def load_matches():
    rows = database.fetch_rows(
        table_name="matches",
        columns=(
            "match_id, home_team_id, away_team_id, home_score, away_score, "
            "match_date, competition_id, season_id"
        ),
    )
    df = pd.DataFrame(rows)
    return df


@st.cache_data(ttl=300)
def load_players():
    rows = database.fetch_rows(
        table_name="players",
        columns="statsbomb_player_id, player_name, position_id, position_name",
    )
    df = pd.DataFrame(rows)
    return df


@st.cache_data(ttl=300)
def load_shot_by_match(match_id: str):
    return database.fetch_rows_by_column(
        table_name="shots",
        column="match_id",
        value=match_id,
        columns="*",
    )
