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
    from football_analytics.streamlit.theme import inject_app_styles
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

ICON_PATH = Path(__file__).resolve().parent / "icon_512.png"
st.set_page_config(
    page_title="Football Analysis", page_icon=str(ICON_PATH), layout="wide"
)


def render_home() -> None:
    inject_app_styles()
    st.markdown(
        f"""
        <h1 class="page-title">Football Analytics</h1>
        <p class="page-caption">
            Explore match intelligence from StatsBomb and market data from Transfermarkt
            in one dashboard. Use the sidebar to switch sections.
        </p>
        <div class="hero-panel">
            <h2>Getting started</h2>
            <p>
                Pick a data source below, then use the filters on each page to narrow
                competitions, seasons, clubs, or players. Match Details includes shot maps,
                xG progression, and live model selection.
            </p>
        </div>
        <div class="nav-tile-grid">
            <div class="nav-tile">
                <div class="nav-tile-title">StatsBomb</div>
                <p class="nav-tile-desc">
                    Teams, player search, and per-match shot analytics with custom xG models.
                </p>
            </div>
            <div class="nav-tile">
                <div class="nav-tile-title">Transfermarkt</div>
                <p class="nav-tile-desc">
                    Player profiles, market values, and transfer views (values and transfers
                    pages are being expanded).
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
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

navigation = st.navigation(pages, position="sidebar")
navigation.run()
