"""Shared layout and styling for the Streamlit dashboard."""

from __future__ import annotations

from html import escape
import base64
from pathlib import Path

import streamlit as st

# Brand palette (aligned with apps/streamlit/.streamlit/config.toml)
BRAND_RED = "#E30613"
BRAND_NAVY = "#0B1C2D"
BRAND_MUTED = "rgba(11, 28, 45, 0.62)"
BRAND_BORDER = "rgba(11, 28, 45, 0.1)"
BRAND_SURFACE = "#F2F4F7"
BRAND_CARD_BG = "#FFFFFF"

_APP_STYLES_INJECTED = False


def inject_app_styles(*, force: bool = False, content_max_width_px: int = 1180) -> None:
    """Inject global CSS once per session (typography, layout, cards, sidebar)."""
    global _APP_STYLES_INJECTED
    if _APP_STYLES_INJECTED and not force:
        return
    _APP_STYLES_INJECTED = True

    st.markdown(
        f"""
<style>
:root {{
    --fa-brand: {BRAND_RED};
    --fa-navy: {BRAND_NAVY};
    --fa-muted: {BRAND_MUTED};
    --fa-border: {BRAND_BORDER};
    --fa-surface: {BRAND_SURFACE};
    --fa-card-bg: {BRAND_CARD_BG};
    --fa-page-bg: #FAFBFC;
    --fa-radius: 12px;
    --fa-radius-lg: 16px;
    --fa-space-1: 0.35rem;
    --fa-space-2: 0.6rem;
    --fa-space-3: 0.9rem;
    --fa-space-4: 1.2rem;
    --fa-shadow: 0 1px 2px rgba(11, 28, 45, 0.06),
        0 4px 14px rgba(11, 28, 45, 0.05);
}}

/* Layout */
.stApp {{
    background: linear-gradient(180deg, var(--fa-page-bg) 0%, #F6F8FB 100%);
}}
.block-container {{
    padding-top: 0.85rem;
    padding-bottom: 2.4rem;
    max-width: {content_max_width_px}px;
}}
div[data-testid="stMainBlockContainer"] {{
    padding-top: 0.15rem !important;
}}

/* Keep vertical spacing between sections predictable across pages */
div[data-testid="stVerticalBlock"] > div {{
    margin-top: var(--fa-space-2);
    margin-bottom: var(--fa-space-2);
}}
.block-container > div[data-testid="stVerticalBlock"] > div:first-child {{
    margin-top: 0;
}}

/* Header / toolbar */
header[data-testid="stHeader"] {{
    background: rgba(250, 251, 252, 0.92);
    border-bottom: 1px solid var(--fa-border);
}}

/* Sidebar */
section[data-testid="stSidebar"] > div {{
    border-right: 1px solid var(--fa-border);
    background: linear-gradient(180deg, #fafbfc 0%, #f4f6f9 100%);
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {{
    padding-top: 0.35rem;
    padding-left: 0.3rem;
    padding-right: 0.3rem;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] span {{
    font-weight: 600;
    letter-spacing: 0.01em;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
    padding-top: 0.5rem;
}}
.sidebar-brand {{
    padding: 0.15rem 0.35rem 0.5rem;
    margin: 0 0.2rem 0.45rem;
    display: flex;
    flex-direction: column;
    align-items: center;
}}
.sidebar-brand-logo {{
    width: 64px;
    height: 64px;
    border-radius: 12px;
    border: 1px solid var(--fa-border);
    background: #ffffff;
    object-fit: cover;
    display: block;
    margin-bottom: 0.28rem;
}}
.sidebar-brand-title {{
    font-size: 0.82rem;
    font-weight: 700;
    color: var(--fa-navy);
    letter-spacing: 0.01em;
    line-height: 1.15;
    text-align: center;
}}

/* Typography */
h1, .page-title {{
    font-weight: 700;
    letter-spacing: -0.025em;
    color: var(--fa-navy);
    margin-top: 0;
    margin-bottom: 0.35rem;
}}
h2, h3 {{
    color: var(--fa-navy);
    letter-spacing: -0.015em;
}}
h2 {{
    margin-top: 1.25rem;
    margin-bottom: 0.65rem;
    font-size: 1.15rem;
    font-weight: 600;
}}
h3 {{
    margin-top: 0.5rem;
    margin-bottom: 0.5rem;
    font-size: 1.02rem;
    font-weight: 600;
}}
.page-caption {{
    color: var(--fa-muted);
    font-size: 1.02rem;
    line-height: 1.5;
    margin: 0 0 1.35rem 0;
    max-width: 52rem;
}}
.page-header {{
    margin-top: -3.0rem;
    margin-bottom: -0.9rem;
}}
.page-header .page-caption {{
    margin-bottom: 1.1rem;
}}
.section-title {{
    margin-top: 0.35rem;
    margin-bottom: 0.7rem;
    margin-left: 0.25rem;
    display: block;
    width: auto;
    max-width: 100%;
    padding: 0.1rem 0;
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--fa-navy);
    border: none;
    background: transparent;
    border-radius: 0;
}}
hr {{
    margin: 1.7rem 0 1.25rem;
    border: none;
    border-top: 1px solid var(--fa-border);
}}

/* Form and filter controls */
div[data-testid="stSelectbox"],
div[data-testid="stTextInput"],
div[data-testid="stNumberInput"],
div[data-testid="stDateInput"],
div[data-testid="stSlider"] {{
    margin-bottom: 0.2rem;
}}
div[data-testid="stWidgetLabel"] {{
    margin-bottom: 0.1rem;
}}
div[data-testid="stWidgetLabel"] p {{
    font-size: 0.8rem;
    margin-bottom: 0;
}}
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div {{
    min-height: 2.05rem;
}}
div[data-testid="stSlider"] {{
    padding-top: 0.04rem;
}}

/* Compact sidebar filter stack */
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {{
    margin-top: 0.18rem;
    margin-bottom: 0.18rem;
}}
section[data-testid="stSidebar"] h3 {{
    margin-top: 0.14rem;
    margin-bottom: 0.22rem;
}}

/* Tabs */
div[data-baseweb="tab-list"] {{
    gap: 0.4rem;
    border-bottom: 1px solid var(--fa-border);
    padding-bottom: 0.22rem;
    margin-bottom: 0.35rem;
}}
button[data-baseweb="tab"] {{
    border: 1px solid transparent;
    border-radius: 999px;
    background: transparent;
    padding: 0.3rem 0.8rem;
    height: auto;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    border-color: rgba(227, 6, 19, 0.28);
    background: rgba(227, 6, 19, 0.08);
}}
div[data-baseweb="tab-panel"] {{
    padding-top: 0.04rem;
}}

/* Hero (home) */
.hero-panel {{
    border: 1px solid var(--fa-border);
    border-radius: var(--fa-radius-lg);
    padding: 1.35rem 1.5rem;
    background: linear-gradient(135deg, #ffffff 0%, #f7f9fc 55%, #f2f5f9 100%);
    box-shadow: var(--fa-shadow);
    margin-bottom: 1.25rem;
}}
.hero-panel h2 {{
    margin-top: 0;
    margin-bottom: 0.45rem;
    font-size: 1.35rem;
}}
.hero-panel p {{
    color: var(--fa-muted);
    margin: 0;
    line-height: 1.55;
    max-width: 40rem;
}}
.nav-tile-grid {{
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.85rem;
    margin-top: 0.25rem;
}}
@media (max-width: 720px) {{
    .nav-tile-grid {{
        grid-template-columns: 1fr;
    }}
}}
.nav-tile {{
    border: 1px solid var(--fa-border);
    border-radius: var(--fa-radius);
    padding: 0.95rem 1rem;
    background: var(--fa-card-bg);
    box-shadow: var(--fa-shadow);
}}
.nav-tile-title {{
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--fa-navy);
    margin-bottom: 0.3rem;
}}
.nav-tile-desc {{
    font-size: 0.88rem;
    color: var(--fa-muted);
    line-height: 1.4;
    margin: 0;
}}

/* Cards (match stats, info panels) */
.card {{
    border: 1px solid var(--fa-border);
    border-radius: var(--fa-radius);
    padding: 1.05rem 1.1rem;
    background: var(--fa-card-bg);
    box-shadow: var(--fa-shadow);
}}
.card-spaced {{
    margin-bottom: 1rem;
}}
.stat-card {{
    min-height: 262px;
    height: 262px;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    padding-bottom: 0.65rem;
}}
.stat-title {{
    font-size: 0.92rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--fa-muted);
    margin-bottom: 0.55rem;
    line-height: 1.2;
}}
.stat-primary {{
    font-size: 1.45rem;
    font-weight: 800;
    line-height: 1.1;
    margin-bottom: 0.25rem;
    color: var(--fa-navy);
}}
.score-card {{
    justify-content: flex-start;
    align-items: stretch;
    text-align: left;
}}
.score-body {{
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}}
.scoreline-big {{
    font-size: 3.6rem;
    font-weight: 800;
    line-height: 0.95;
    margin: 0;
    text-align: center;
    width: 100%;
    color: var(--fa-navy);
    letter-spacing: -0.03em;
}}
.score-sub {{
    text-align: center;
    margin-top: 0.35rem;
}}
.stat-secondary {{
    font-size: 0.9rem;
    color: var(--fa-muted);
}}
.stat-table-wrap {{
    flex: 0 0 auto;
    display: flex;
    align-items: flex-start;
    padding-top: 0.1rem;
    padding-bottom: 0.08rem;
}}
.stat-grid {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.95rem;
}}
.stat-grid th,
.stat-grid td {{
    padding: 0.28rem 0.38rem;
    text-align: center;
    border-bottom: 1px solid var(--fa-border);
}}
.stat-grid th {{
    font-size: 0.75rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--fa-muted);
    font-weight: 600;
}}
.stat-grid th:first-child,
.stat-grid td:first-child {{
    text-align: left;
}}
.stat-grid td:first-child {{
    font-weight: 500;
    color: var(--fa-navy);
}}
.stat-grid tbody tr:first-child td {{
    font-size: 1rem;
}}
.stat-grid tbody tr:last-child td {{
    border-bottom: 1px solid var(--fa-border);
    padding-bottom: 0.24rem;
}}
.match-info {{
    display: grid;
    grid-template-columns: repeat(3, minmax(140px, 1fr));
    gap: 0.55rem 0.9rem;
    font-size: 0.92rem;
}}
.match-info div {{
    line-height: 1.3;
}}
.match-info strong {{
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--fa-muted);
    font-weight: 600;
}}

/* Player profile cards (Transfermarkt) */
.player-card-section {{
    margin-bottom: 1.2rem;
}}
.player-card {{
    border: 1px solid var(--fa-border);
    border-radius: var(--fa-radius-lg);
    padding: 1.1rem 1.2rem;
    background: var(--fa-card-bg);
    box-shadow: var(--fa-shadow);
    margin-bottom: 0.7rem;
    min-height: 300px;
}}
.player-card-title {{
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--fa-navy);
    margin-bottom: 0.7rem;
}}
.player-card-metric {{
    font-size: 1.02rem;
    font-weight: 600;
    color: var(--fa-navy);
    margin-bottom: 0.2rem;
}}
.player-card-label {{
    font-size: 0.82rem;
    color: var(--fa-muted);
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin-bottom: 0.15rem;
}}
.player-metric-grid {{
    display: grid;
    grid-template-columns: repeat(4, minmax(120px, 1fr));
    gap: 0.75rem;
}}
.player-metric-tile {{
    border: 1px solid var(--fa-border);
    border-radius: var(--fa-radius);
    padding: 0.55rem 0.65rem;
    background: var(--fa-surface);
    min-height: 68px;
}}
.player-image-card {{
    border: 1px solid var(--fa-border);
    border-radius: var(--fa-radius-lg);
    padding: 0.18rem;
    background: var(--fa-card-bg);
    box-shadow: var(--fa-shadow);
    height: 300px;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
}}
.player-image {{
    max-height: 100%;
    max-width: 100%;
    height: auto;
    width: auto;
    object-fit: contain;
    object-position: center center;
    border-radius: 14px;
}}
@media (max-width: 980px) {{
    .player-metric-grid {{
        grid-template-columns: repeat(2, minmax(120px, 1fr));
    }}
}}

/* Empty / placeholder panels */
.placeholder-panel {{
    border: 1px dashed var(--fa-border);
    border-radius: var(--fa-radius);
    padding: 1.4rem 1.25rem;
    background: var(--fa-surface);
    color: var(--fa-muted);
    line-height: 1.5;
}}

/* Dataframe and charts */
div[data-testid="stDataFrame"] {{
    border: 1px solid var(--fa-border);
    border-radius: var(--fa-radius);
    overflow: hidden;
    box-shadow: var(--fa-shadow);
    background: var(--fa-card-bg);
}}
</style>
""",
        unsafe_allow_html=True,
    )


def page_header(
    title: str,
    subtitle: str | None = None,
    *,
    content_max_width_px: int = 1180,
    margin_top: str = "-3.0rem",
    margin_bottom: str = "-0.9rem",
) -> None:
    """Render a consistent page title and optional caption."""
    inject_app_styles(content_max_width_px=content_max_width_px)
    subtitle_html = (
        f'<p class="page-caption">{escape(subtitle)}</p>' if subtitle else ""
    )
    st.markdown(
        f'<div class="page-header" style="margin-top: {margin_top}; margin-bottom: {margin_bottom};"><h1 class="page-title">{escape(title)}</h1>{subtitle_html}</div>',
        unsafe_allow_html=True,
    )


def section_heading(title: str, *, level: int = 3) -> None:
    """Render a section heading with brand accent."""
    inject_app_styles()
    tag = f"h{min(max(level, 2), 4)}"
    st.markdown(
        f'<{tag} class="section-title">{escape(title)}</{tag}>',
        unsafe_allow_html=True,
    )


def inject_sidebar_navigation_brand(
    icon_path: str | Path,
    *,
    nav_padding_top: str = "2.0rem",
    logo_top: str = "1.1rem",
    logo_left: str = "0.55rem",
    logo_size_px: int = 64,
) -> None:
    """Render the sidebar logo above navigation with consistent spacing."""
    inject_app_styles()
    encoded_icon = base64.b64encode(Path(icon_path).read_bytes()).decode("ascii")
    st.markdown(
        f"""
        <style>
        section[data-testid="stSidebar"] > div {{
            position: relative;
        }}
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {{
            padding-top: {nav_padding_top};
        }}
        section[data-testid="stSidebar"] > div::before {{
            content: "";
            position: absolute;
            top: {logo_top};
            left: {logo_left};
            width: {logo_size_px}px;
            height: {logo_size_px}px;
            border-radius: 12px;
            border: 1px solid rgba(11, 28, 45, 0.12);
            background: #ffffff url("data:image/png;base64,{encoded_icon}") center/cover no-repeat;
            box-shadow: 0 1px 2px rgba(11, 28, 45, 0.06), 0 4px 14px rgba(11, 28, 45, 0.05);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
