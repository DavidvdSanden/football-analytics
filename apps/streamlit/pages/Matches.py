from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

from football_analytics.utils import helper, visuals

st.title("Matches")


def _parse_shot_row(row: dict) -> dict:
    for key in ("shot", "location", "player", "team"):
        if key in row:
            row[key] = helper.parse_json_field(row[key])

    shot = row.get("shot")
    if isinstance(shot, dict):
        for key in ("freeze_frame", "end_location"):
            if key in shot:
                shot[key] = helper.parse_json_field(shot[key])

    return row


def display_shot_by_id(
    shot_id: str,
    table_name: str = "shots",
    id_column: str = "shot_id",
) -> None:
    supabase = helper.get_supabase_client()
    response = (
        supabase.table(table_name)
        .select("*")
        .eq(id_column, shot_id)
        .limit(1)
        .execute()
    )
    data = response.data or []
    if not data:
        st.warning(f"No shot found for {id_column}={shot_id}.")
        return

    shot_row = _parse_shot_row(data[0])

    raw = shot_row.get("full_json")
    shot_payload = helper.parse_json_field(raw)

    if not isinstance(shot_payload, dict):
        st.error("full_json is not a valid JSON object.")
        return

    fig = visuals.plot_shot_details(shot_payload, show=False)
    st.plotly_chart(fig, use_container_width=True)


st.subheader("Shot Visual")
with st.form("shot_lookup"):
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        shot_id = st.text_input("Shot ID", "")
    with col_b:
        table_name = st.text_input("Shot table", "shots")
    with col_c:
        id_column = st.text_input("ID column", "statsbomb_event_id")
    submitted = st.form_submit_button("Show shot")

if submitted:
    if not shot_id.strip():
        st.warning("Please enter a shot ID.")
    else:
        display_shot_by_id(shot_id.strip(), table_name=table_name, id_column=id_column)
