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

from football_analytics.utils import database

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


@st.cache_data(ttl=300)
def load_table(table_name: str, columns: str = "*") -> pd.DataFrame:
    rows = database.fetch_rows(table_name=table_name, columns=columns)
    return pd.DataFrame(rows)


def _format_number(value: int | float) -> str:
    return f"{int(value):,}"


def _coerce_datetime(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(dtype="datetime64[ns, UTC]")
    return pd.to_datetime(df[column], errors="coerce", utc=True)


def _last_timestamp(df: pd.DataFrame, date_columns: list[str]) -> tuple[str, str]:
    for date_column in date_columns:
        if date_column not in df.columns:
            continue
        timestamps = _coerce_datetime(df, date_column)
        if timestamps.notna().any():
            latest_ts = timestamps.max()
            return date_column, latest_ts.strftime("%Y-%m-%d %H:%M UTC")
    return "N/A", "N/A"


def _recent_rows(df: pd.DataFrame, date_columns: list[str], cutoff: pd.Timestamp) -> pd.DataFrame:
    for date_column in date_columns:
        if date_column not in df.columns:
            continue
        timestamps = _coerce_datetime(df, date_column)
        if timestamps.notna().any():
            return df.loc[timestamps >= cutoff].copy()
    return pd.DataFrame(columns=df.columns)


def _format_delta(delta: int) -> tuple[str, str, str]:
    if delta > 0:
        return f"+{delta}", "#137333", "&uarr;"
    if delta < 0:
        return str(delta), "#B3261E", "&darr;"
    return "0", "#5F6368", "&rarr;"


page_header(
    "Transfermarkt Database",
    "Overview of core Transfermarkt tables and a snapshot of additions from the last 7 days.",
    content_max_width_px=1320,
)

table_specs = [
    {
        "label": "Clubs",
        "table": "transfermarkt.clubs",
        "columns": "tm_club_id, club_name, country, scraped_at",
        "date_columns": ["scraped_at"],
        "preview": ["tm_club_id", "club_name", "country", "scraped_at"],
    },
    {
        "label": "Players",
        "table": "transfermarkt.players",
        "columns": "tm_player_id, full_name, nationality, current_tm_club_id, updated_at, scraped_at",
        "date_columns": ["updated_at", "scraped_at"],
        "preview": [
            "tm_player_id",
            "full_name",
            "nationality",
            "current_tm_club_id",
            "updated_at",
            "scraped_at",
        ],
    },
    {
        "label": "Market Values",
        "table": "transfermarkt.player_market_values",
        "columns": "tm_player_id, valuation_date, market_value_eur, scraped_at",
        "date_columns": ["scraped_at", "valuation_date"],
        "preview": [
            "tm_player_id",
            "name",
            "club_name",
            "valuation_date",
            "market_value_eur",
            "scraped_at",
        ],
    },
    {
        "label": "Latest Transfers",
        "table": "transfermarkt.latest_transfers",
        "columns": "transfer_uid, player_name, from_club_name, to_club_name, transfer_date, transfer_fee_eur, scraped_at",
        "date_columns": ["scraped_at", "transfer_date"],
        "preview": [
            "transfer_uid",
            "player_name",
            "from_club_name",
            "to_club_name",
            "transfer_date",
            "transfer_fee_eur",
            "scraped_at",
        ],
    },
]

loaded_tables: dict[str, pd.DataFrame] = {}
overview_rows: list[dict[str, str]] = []
cutoff = pd.Timestamp.utcnow() - pd.Timedelta(days=7)

section_heading("Database Overview")
metric_columns = st.columns(len(table_specs))
for idx, spec in enumerate(table_specs):
    table_df = load_table(spec["table"], spec["columns"])
    loaded_tables[spec["table"]] = table_df
    date_col, last_update_text = _last_timestamp(table_df, spec["date_columns"])
    recent_df = _recent_rows(table_df, spec["date_columns"], cutoff)
    delta_text, delta_color, delta_indicator = _format_delta(len(recent_df))
    total_rows = len(table_df)

    with metric_columns[idx]:
        st.markdown(
            f"""
            <div class="card" style="padding: 0.9rem 1rem; min-height: 114px;">
                <div class="player-card-label" style="margin-bottom: 0.25rem;">{spec['label']}</div>
                <div style="display:flex; align-items:baseline; gap:0.45rem; margin-bottom:0.25rem;">
                    <span style="font-size:1.55rem; font-weight:800; color:#0B1C2D; line-height:1;">{_format_number(total_rows)}</span>
                    <span style="font-size:0.95rem; font-weight:700; color:{delta_color}; line-height:1;">{delta_indicator} ({delta_text})</span>
                </div>
                <div style="font-size:0.8rem; color:rgba(11, 28, 45, 0.62);">Last 7 days</div>
                <div style="font-size:0.76rem; color:rgba(11, 28, 45, 0.62); margin-top:0.2rem;">Latest: {last_update_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    overview_rows.append(
        {
            "Dataset": spec["label"],
            "Table": spec["table"],
            "Rows": _format_number(total_rows),
            "7d Change": f"{delta_indicator} {delta_text}",
            "Latest Field": date_col,
            "Latest Activity": last_update_text,
        }
    )

st.dataframe(pd.DataFrame(overview_rows), use_container_width=True, hide_index=True)

section_heading("Last 7 Days Additions")
recent_summary_rows: list[dict[str, str]] = []
tabs = st.tabs([spec["label"] for spec in table_specs])

for spec, tab in zip(table_specs, tabs):
    table_df = loaded_tables[spec["table"]]
    recent_df = _recent_rows(table_df, spec["date_columns"], cutoff)
    recent_summary_rows.append(
        {
            "Dataset": spec["label"],
            "Added/Updated Rows": _format_number(len(recent_df)),
            "Window Start": cutoff.strftime("%Y-%m-%d %H:%M UTC"),
        }
    )

    with tab:
        if recent_df.empty:
            st.info("No additions found in the last 7 days.")
            continue

        display_df = recent_df
        if spec["table"] == "transfermarkt.player_market_values":
            players_df = loaded_tables.get("transfermarkt.players", pd.DataFrame())
            clubs_df = loaded_tables.get("transfermarkt.clubs", pd.DataFrame())
            if (
                not players_df.empty
                and "tm_player_id" in display_df.columns
                and "tm_player_id" in players_df.columns
            ):
                player_cols = ["tm_player_id"]

                if "full_name" in players_df.columns:
                    source_name_col = "full_name"
                elif "name" in players_df.columns:
                    source_name_col = "name"
                else:
                    source_name_col = None

                if source_name_col:
                    player_cols.append(source_name_col)

                player_club_col = None
                if "current_tm_club_id" in players_df.columns:
                    player_club_col = "current_tm_club_id"
                elif "tm_club_id" in players_df.columns:
                    player_club_col = "tm_club_id"
                if player_club_col:
                    player_cols.append(player_club_col)

                player_lookup = (
                    players_df[player_cols]
                    .dropna(subset=["tm_player_id"])
                    .drop_duplicates(subset=["tm_player_id"], keep="last")
                )
                rename_map = {}
                if source_name_col:
                    rename_map[source_name_col] = "name"
                if player_club_col:
                    rename_map[player_club_col] = "player_tm_club_id"
                if rename_map:
                    player_lookup = player_lookup.rename(columns=rename_map)

                display_df = display_df.merge(
                    player_lookup,
                    on="tm_player_id",
                    how="left",
                )

                if (
                    "player_tm_club_id" in display_df.columns
                    and not clubs_df.empty
                    and "tm_club_id" in clubs_df.columns
                    and "club_name" in clubs_df.columns
                ):
                    display_df["player_tm_club_id"] = pd.to_numeric(
                        display_df["player_tm_club_id"], errors="coerce"
                    ).astype("Int64")
                    club_lookup = (
                        clubs_df[["tm_club_id", "club_name"]]
                        .dropna(subset=["tm_club_id", "club_name"])
                        .drop_duplicates(subset=["tm_club_id"], keep="last")
                        .rename(columns={"tm_club_id": "player_tm_club_id"})
                    )
                    club_lookup["player_tm_club_id"] = pd.to_numeric(
                        club_lookup["player_tm_club_id"], errors="coerce"
                    ).astype("Int64")
                    display_df = display_df.merge(
                        club_lookup,
                        on="player_tm_club_id",
                        how="left",
                    )

        preview_columns = [col for col in spec["preview"] if col in display_df.columns]
        sort_column = next(
            (col for col in spec["date_columns"] if col in display_df.columns),
            preview_columns[-1],
        )
        table_preview = (
            display_df[preview_columns]
            .sort_values(by=sort_column, ascending=False)
            .head(200)
            .copy()
        )
        if "market_value_eur" in table_preview.columns:
            numeric_values = pd.to_numeric(table_preview["market_value_eur"], errors="coerce")
            table_preview["market_value_eur"] = numeric_values.apply(
                lambda value: f"{int(value):,}".replace(",", ".") if pd.notna(value) else ""
            )
        st.dataframe(
            table_preview,
            use_container_width=True,
            hide_index=True,
        )

st.dataframe(pd.DataFrame(recent_summary_rows), use_container_width=True, hide_index=True)
