from pathlib import Path
import importlib
import importlib.util
import sys

import streamlit as st

# Ensure src/ is importable no matter where Streamlit is launched from.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

try:
    from football_analytics.streamlit.theme import (
        inject_app_styles,
        inject_sidebar_navigation_brand,
        page_header,
        section_heading,
    )
except ModuleNotFoundError:
    package_root = str(SRC_PATH / "football_analytics")
    loaded_pkg = sys.modules.get("football_analytics")
    if loaded_pkg is not None and hasattr(loaded_pkg, "__path__"):
        pkg_paths = [str(p) for p in loaded_pkg.__path__]
        if package_root not in pkg_paths:
            loaded_pkg.__path__.append(package_root)
    importlib.invalidate_caches()
    theme_path = SRC_PATH / "football_analytics" / "streamlit" / "theme.py"
    spec = importlib.util.spec_from_file_location(
        "football_analytics.streamlit.theme", theme_path
    )
    if spec is None or spec.loader is None:
        raise
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    inject_app_styles = module.inject_app_styles
    inject_sidebar_navigation_brand = module.inject_sidebar_navigation_brand
    page_header = module.page_header
    section_heading = module.section_heading

ICON_PATH = Path(__file__).resolve().parent / "icon_512.png"
st.set_page_config(
    page_title="Football Analysis", page_icon=str(ICON_PATH), layout="wide"
)
inject_app_styles()


def render_home() -> None:
    inject_app_styles()
    page_header(
        "Football Analytics",
        "Explore match intelligence from StatsBomb and market data from Transfermarkt in one dashboard.",
    )

    st.markdown(
        """
        <div class="hero-panel">
            <h2>Getting started</h2>
            <p>
                Choose a section below to jump directly into team performance, player analysis,
                or market movement. Use each page's filters to narrow competitions, seasons,
                clubs, and players.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    section_heading("Jump to pages")
    stats_col, tm_col = st.columns(2)

    with stats_col:
        st.markdown(
            """
            <div class="nav-tile">
                <div class="nav-tile-title">StatsBomb</div>
                <p class="nav-tile-desc">
                    Teams, player search, and per-match shot analytics with custom xG models.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link("pages/Statsbomb/Teams.py", label="Open Teams", icon=":material/groups:")
        st.page_link(
            "pages/Statsbomb/Match Details.py",
            label="Open Match Details",
            icon=":material/sports_soccer:",
        )
        st.page_link("pages/Statsbomb/Players.py", label="Open Players", icon=":material/person:")

    with tm_col:
        st.markdown(
            """
            <div class="nav-tile">
                <div class="nav-tile-title">Transfermarkt</div>
                <p class="nav-tile-desc">
                    Player profiles, market values, transfers, and database exploration tools.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link(
            "pages/Transfermarkt/Database.py",
            label="Open Database",
            icon=":material/storage:",
        )
        st.page_link(
            "pages/Transfermarkt/Players.py",
            label="Open Players",
            icon=":material/person_search:",
        )
        st.page_link(
            "pages/Transfermarkt/Transfers.py",
            label="Open Transfers",
            icon=":material/compare_arrows:",
        )
        st.page_link(
            "pages/Transfermarkt/Values.py",
            label="Open Values",
            icon=":material/payments:",
        )

    section_heading("What you can do here")
    info_col_1, info_col_2 = st.columns(2)
    with info_col_1:
        st.markdown(
            """
            - Track team and player output with match-level context.
            - Inspect shot quality and xG evolution in individual fixtures.
            - Compare tactical and finishing signals across matches.
            """
        )
    with info_col_2:
        st.markdown(
            """
            - Explore market value trends and transfer activity.
            - Review player profiles with club and valuation details.
            - Move quickly between analytics and recruitment perspectives.
            """
        )

    st.caption(
        "Tip: Use the sidebar for full navigation, and use the quick links above to jump straight to your most-used pages."
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
            "pages/Transfermarkt/Database.py",
            title="Database",
            icon=":material/storage:",
            url_path="transfermarkt-database",
        ),
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

inject_sidebar_navigation_brand(ICON_PATH)
navigation = st.navigation(pages, position="sidebar")
navigation.run()
