from supabase import create_client, Client
import streamlit as st
import pandas as pd


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
def load_players():
    response = (
        supabase.table("players")
        .select("statsbomb_player_id, player_name, position_id, position_name")
        .execute()
    )
    df = pd.DataFrame(response.data)
    return df


@st.cache_data(ttl=300)
def load_shot_by_match(match_id: str):
    response = supabase.table("shots").select("*").eq("match_id", match_id).execute()
    return response.data
