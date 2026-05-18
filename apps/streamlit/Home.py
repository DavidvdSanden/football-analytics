from pathlib import Path

import streamlit as st

ICON_PATH = Path(__file__).resolve().parent / "icon_512.png"
st.set_page_config(
    page_title="Football Analysis", page_icon=str(ICON_PATH), layout="wide"
)


def render_home() -> None:
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
        "Welcome to the Streamlit dashboard. Use the grouped sidebar navigation "
        "to move between Statsbomb and Transfermarkt pages."
    )
    st.info(
        "The app now uses Streamlit navigation sections so related pages appear under "
        "separate headings in the sidebar."
    )


pages = {
    "Home": [
        st.Page(
            render_home,
            title="Home",
            icon=":material/home:",
            url_path="home",
            default=True,
        )
    ],
    "Statsbomb": [
        st.Page(
            "pages/Statsbomb/Teams.py",
            title="Teams",
            icon=":material/groups:",
            url_path="statsbomb-teams",
        ),
        st.Page(
            "pages/Statsbomb/Match Details.py",
            title="Match Details",
            icon=":material/sports_soccer:",
            url_path="statsbomb-match-details",
        ),
        st.Page(
            "pages/Statsbomb/Players.py",
            title="Players",
            icon=":material/person:",
            url_path="statsbomb-players",
        ),
    ],
    "Transfermarkt": [
        st.Page(
            "pages/Transfermarkt/Players.py",
            title="Players",
            icon=":material/person_search:",
            url_path="transfermarkt-players",
        ),
        st.Page(
            "pages/Transfermarkt/Transfers.py",
            title="Transfers",
            icon=":material/compare_arrows:",
            url_path="transfermarkt-transfers",
        ),
        st.Page(
            "pages/Transfermarkt/Values.py",
            title="Values",
            icon=":material/payments:",
            url_path="transfermarkt-values",
        ),
    ],
}

navigation = st.navigation(pages, position="sidebar")
navigation.run()
