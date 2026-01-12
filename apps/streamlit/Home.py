from pathlib import Path

import streamlit as st

ICON_PATH = Path(__file__).resolve().parent / "icon_512.png"
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
</style>
""",
    unsafe_allow_html=True,
)
st.title("Football Analytics")
st.write(
    "Welcome to the Streamlit dashboard. Use the pages in the sidebar to explore "
    "teams, clubs, matches, and other analytics."
)

st.subheader("Quick Links")
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.page_link("pages/Teams.py", label="Teams", icon=":material/groups:")
with col_b:
    st.page_link(
        "pages/Match Details.py", label="Match Details", icon=":material/sports_soccer:"
    )
with col_c:
    st.page_link("pages/Players.py", label="Players", icon=":material/person:")
