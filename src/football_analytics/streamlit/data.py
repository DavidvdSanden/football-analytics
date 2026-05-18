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
        columns=(
            "statsbomb_player_id, player_name, position_id, position_name, "
            "team_id, team_name, jersey_number"
        ),
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


@st.cache_data(ttl=300)
def load_transfermarkt_players():
    rows = database.fetch_rows(
        table_name="transfermarkt.players",
        columns=(
            "tm_player_id, full_name, date_of_birth, nationality, preferred_foot, "
            "main_position, detailed_position, current_tm_club_id, contract_expires_on, "
            "player_image_url"
        ),
    )
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def load_transfermarkt_clubs():
    rows = database.fetch_rows(
        table_name="transfermarkt.clubs",
        columns="tm_club_id, club_name, country",
    )
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def load_transfermarkt_market_values():
    rows = database.fetch_rows(
        table_name="transfermarkt.player_market_values",
        columns="tm_player_id, valuation_date, market_value_eur",
    )
    return pd.DataFrame(rows)
