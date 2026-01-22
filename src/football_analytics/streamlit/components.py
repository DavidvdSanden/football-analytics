import streamlit as st
import streamlit.components.v1 as components
import textwrap


def match_header(home_team, away_team, home_goals, away_goals, render=True):
    html = f"""
        <div style="width:100%; text-align:center;">
            <!-- Team names -->
            <div style="
                display: grid;
                grid-template-columns: 1fr auto 1fr;
                align-items: center;
                font-size: 16px;
                font-weight: 600;
                margin-bottom: 0.25rem;
            ">
                <div style="text-align: right; padding-right: 0.5rem;">{home_team}</div>
                <div style="opacity: 0.6; text-align: center;">–</div>
                <div style="text-align: left; padding-left: 0.5rem;">{away_team}</div>
            </div>
            <!-- Score -->
            <div style="
                display: grid;
                grid-template-columns: 1fr auto 1fr;
                align-items: center;
                font-size: 80px;
                font-weight: 800;
                line-height: 1;
            ">
                <div style="text-align: right; padding-right: 0.5rem;">{home_goals}</div>
                <div style="opacity: 0.6; text-align: center;">–</div>
                <div style="text-align: left; padding-left: 0.5rem;">{away_goals}</div>
            </div>
        </div>
        """
    html = textwrap.dedent(html)
    if render:
        st.markdown(html, unsafe_allow_html=True)
    return html


def enable_plotly_auto_resize():
    html = """
        <script>
        (function () {
            const parentDoc = window.parent.document;
            const target =
                parentDoc.querySelector('[data-testid="stMain"]') ||
                parentDoc.querySelector('section.main') ||
                parentDoc.body;
            const plotly = window.parent.Plotly;
            if (!target || !plotly) return;

            const resizePlots = () => {
                const plots = parentDoc.querySelectorAll('.js-plotly-plot');
                plots.forEach((p) => {
                    if (p && p.data) {
                        plotly.Plots.resize(p);
                    }
                });
            };

            const ro = new ResizeObserver(resizePlots);
            ro.observe(target);
            window.parent.addEventListener('resize', resizePlots);
            resizePlots();
        })();
        </script>
    """
    components.html(textwrap.dedent(html), height=0, width=0)
