from pathlib import Path
import importlib
import importlib.util
import sys

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

import streamlit as st

try:
    from football_analytics.streamlit.theme import (
        inject_sidebar_navigation_brand,
        page_header,
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

ICON_PATH = Path(__file__).resolve().parents[2] / "icon_512.png"
st.set_page_config(
    page_title="Football Analysis", page_icon=str(ICON_PATH), layout="wide"
)
inject_sidebar_navigation_brand(ICON_PATH)

page_header(
    "Transfermarkt Transfers",
    "Transfer history, move tracking, and squad changes.",
    content_max_width_px=1320,
)
st.markdown(
    """
    <div class="placeholder-panel">
        This section is a starter page. Planned views include transfer windows,
        fee summaries, and player movement timelines.
    </div>
    """,
    unsafe_allow_html=True,
)
