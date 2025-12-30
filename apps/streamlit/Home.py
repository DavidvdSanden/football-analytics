import streamlit as st

st.set_page_config(page_title="Football Analytics", layout="wide")

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
    st.page_link("pages/Match Details.py", label="Match Details", icon=":material/sports_soccer:")
with col_c:
    st.page_link("pages/Players.py", label="Players", icon=":material/person:")



