import streamlit as st
import textwrap


def match_header(home_team, away_team, home_goals, away_goals):
    html = f"""
        <div style="width:100%; text-align:center;">
            <!-- Team names -->
            <div style="
                display: grid;
                grid-template-columns: 1fr auto 1fr;
                align-items: center;
                font-size: 22px;
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
    st.markdown(textwrap.dedent(html), unsafe_allow_html=True)
