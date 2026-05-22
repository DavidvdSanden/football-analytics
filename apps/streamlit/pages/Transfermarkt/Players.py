from pathlib import Path
import importlib
import importlib.util
import sys
from html import escape

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

from football_analytics.streamlit.data import (
    load_transfermarkt_clubs,
    load_transfermarkt_market_values,
    load_transfermarkt_players,
)
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

ICON_PATH = Path(__file__).resolve().parents[2] / "icon_512.png"
st.set_page_config(
    page_title="Football Analysis", page_icon=str(ICON_PATH), layout="wide"
)
inject_sidebar_navigation_brand(ICON_PATH)

page_header(
    "Transfermarkt Players",
    "Search players and view market value, club, and contract highlights.",
    content_max_width_px=1320,
)
section_heading("Player Search and Filter")


def format_market_value(value: object) -> str:
    if pd.isna(value):
        return "N/A"
    amount = float(value)
    if amount >= 1_000_000_000:
        return f"EUR {amount / 1_000_000_000:.2f}B"
    if amount >= 1_000_000:
        return f"EUR {amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"EUR {amount / 1_000:.0f}K"
    return f"EUR {amount:.0f}"


def render_selected_player_section(selected_df: pd.DataFrame) -> None:
    selected_row = selected_df.iloc[0]
    card_height_px = 300

    def _safe(value: object, fallback: str = "N/A") -> str:
        if pd.isna(value):
            return fallback
        text = str(value).strip()
        if not text:
            return fallback
        return escape(text)

    col_img, col_tiles = st.columns([0.9, 2.3], gap="large")
    with col_img:
        image_url = selected_row.get("player_image_url")
        # Swap 'small' for 'medium' if present
        if pd.notna(image_url) and str(image_url).strip():
            img_url = str(image_url)
            if "small" in img_url:
                img_url = img_url.replace("small", "medium")
            st.markdown(
                f"""
                <div class="player-image-card" style="height:{card_height_px}px;">
                    <img class="player-image" src="{escape(img_url)}" alt="Player image" />
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="player-image-card" style="height:{card_height_px}px;">
                    <div class="player-card-label">No player picture available.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col_tiles:
        metrics = [
            ("Latest Value", _safe(selected_row.get("latest_market_value_label"))),
            ("Valuation Date", _safe(selected_row.get("latest_valuation_date"))),
            ("Club", _safe(selected_row.get("club_name"), "Unknown")),
            ("Position", _safe(selected_row.get("main_position"), "Unknown")),
            ("Nationality", _safe(selected_row.get("nationality"), "Unknown")),
            ("Foot", _safe(selected_row.get("preferred_foot"), "Unknown")),
            ("Age", _safe(selected_row.get("age"))),
            ("Contract Until", _safe(selected_row.get("contract_expires_on"))),
        ]
        tiles_html = "".join(
            [
                f'<div class="player-metric-tile"><div class="player-card-label">{label}</div><div class="player-card-metric">{value}</div></div>'
                for label, value in metrics
            ]
        )
        st.markdown(
            f"""
            <div class="player-card player-card-section" style="min-height:{card_height_px}px;">
                <div class="player-card-title">Player Highlights</div>
                <div class="player-metric-grid">{tiles_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

players = load_transfermarkt_players()
if players.empty:
    st.warning("No Transfermarkt player data available in table transfermarkt.players.")
    st.stop()

clubs = load_transfermarkt_clubs()
market_values = load_transfermarkt_market_values()

players = players.copy()
players["current_tm_club_id"] = players["current_tm_club_id"].astype(str)

if not clubs.empty and "tm_club_id" in clubs.columns:
    clubs = clubs.copy()
    clubs["tm_club_id"] = clubs["tm_club_id"].astype(str)
    players = players.merge(
        clubs[["tm_club_id", "club_name"]],
        left_on="current_tm_club_id",
        right_on="tm_club_id",
        how="left",
    )
else:
    players["club_name"] = pd.NA

players["display_label"] = players["full_name"].fillna("Unknown player")
players["display_label"] = players["display_label"] + " - " + players[
    "club_name"
].fillna("Unknown club")

if "date_of_birth" in players.columns:
    players["date_of_birth"] = pd.to_datetime(players["date_of_birth"], errors="coerce")
    today = pd.Timestamp.today().normalize()
    players["age"] = ((today - players["date_of_birth"]).dt.days // 365).astype("Int64")
else:
    players["age"] = pd.Series(dtype="Int64")

if not market_values.empty:
    market_values = market_values.copy()
    market_values["valuation_date"] = pd.to_datetime(
        market_values["valuation_date"], errors="coerce"
    )
    market_values["tm_player_id"] = pd.to_numeric(
        market_values["tm_player_id"], errors="coerce"
    )
    market_values = market_values.dropna(subset=["tm_player_id", "valuation_date"])
    latest_values = (
        market_values.sort_values("valuation_date", ascending=False)
        .drop_duplicates(subset=["tm_player_id"], keep="first")
        .rename(
            columns={
                "valuation_date": "latest_valuation_date",
                "market_value_eur": "latest_market_value_eur",
            }
        )
    )
    players["tm_player_id"] = pd.to_numeric(players["tm_player_id"], errors="coerce")
    players = players.merge(
        latest_values[["tm_player_id", "latest_valuation_date", "latest_market_value_eur"]],
        on="tm_player_id",
        how="left",
    )
else:
    players["latest_valuation_date"] = pd.NaT
    players["latest_market_value_eur"] = pd.NA

players["latest_valuation_date"] = pd.to_datetime(
    players["latest_valuation_date"], errors="coerce"
).dt.date
players["latest_market_value_label"] = players["latest_market_value_eur"].apply(
    format_market_value
)

display_columns = [
    col
    for col in (
        "full_name",
        "club_name",
        "nationality",
        "main_position",
        "preferred_foot",
        "age",
        "contract_expires_on",
        "tm_player_id",
    )
    if col in players.columns
]

tab_search, tab_filters = st.tabs(["Search by name", "Filter by club/position/nationality"])

with tab_search:
    query = st.text_input(
        "Search player name",
        placeholder="Type a player name",
    )
    filtered = players
    if query.strip():
        filtered = players[players["full_name"].str.contains(query, case=False, na=False)]

    if filtered.empty:
        st.info("No players match that search.")
    else:
        options = sorted(filtered["display_label"].dropna().unique().tolist())
        selected_label = st.selectbox("Select a player", options=options)
        selected = filtered[filtered["display_label"] == selected_label]
        render_selected_player_section(selected)

with tab_filters:
    filtered = players.copy()

    col_nationality, col_position, col_club = st.columns(3, gap="small")

    nationality_options = sorted(filtered["nationality"].dropna().astype(str).unique().tolist())
    with col_nationality:
        nationality = st.selectbox("Nationality", options=["All"] + nationality_options)
    if nationality != "All":
        filtered = filtered[filtered["nationality"] == nationality]

    position_options = sorted(filtered["main_position"].dropna().astype(str).unique().tolist())
    with col_position:
        position = st.selectbox("Position", options=["All"] + position_options)
    if position != "All":
        filtered = filtered[filtered["main_position"] == position]

    club_options = sorted(filtered["club_name"].dropna().astype(str).unique().tolist())
    with col_club:
        club = st.selectbox("Club", options=["All"] + club_options)
    if club != "All":
        filtered = filtered[filtered["club_name"] == club]

    min_age = int(filtered["age"].dropna().min()) if filtered["age"].notna().any() else 16
    max_age = int(filtered["age"].dropna().max()) if filtered["age"].notna().any() else 45

    selected_age_range = st.slider(
        "Age range",
        min_value=min_age,
        max_value=max_age,
        value=(min_age, max_age),
    )
    filtered = filtered[
        filtered["age"].isna()
        | (
            (filtered["age"] >= selected_age_range[0])
            & (filtered["age"] <= selected_age_range[1])
        )
    ]

    if filtered.empty:
        st.info("No players match the selected filters.")
    else:
        options = sorted(filtered["display_label"].dropna().unique().tolist())
        selected_label = st.selectbox("Select a player", options=options, key="tm_filtered_player")
        selected = filtered[filtered["display_label"] == selected_label]
        render_selected_player_section(selected)
