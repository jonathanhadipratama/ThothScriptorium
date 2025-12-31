from pathlib import Path
import streamlit as st
import plotly.io as pio
from pandas.io.formats.style import Styler
pio.templates.default = "plotly_white"

from src.ui.theme import load_theme_css
from src.ui.components import (
    hero_section,
    load_payload,
    sankey_section,
    commentary_and_snapshot,
    raw_table_section,
)
from src.ui.fundamental_chart import quarterly_fundamental_chart
from src.ui.fundamental_table import render_core_fundamental_table
from src.ui.investment_suggestion import (
    load_investment_suggestion_json,
    render_investment_suggestion,
)
from src.data_extraction import get_bigquery_client, get_all_and_quarterly, PROJECT_ID

# ----------------- Page config -----------------
# st.set_page_config(
#     page_title="Thoth Scriptorium",
#     page_icon="🪶",
#     layout="wide",
# )

DATA_DIR = Path("output")
CODES = ["ULTJ", "MYOR", "CMRY", "UNVR", "INDF", "ICBP", "KEJU", "DMND", "GOOD"]

# ----------------- Theme -----------------
load_theme_css()

# ----------------- Init session state -----------------
if "active_code" not in st.session_state:
    st.session_state.active_code = None

# ----------------- Hero + ticker selection -----------------
code, process_clicked = hero_section(CODES)

# If user clicked the main "Process" button, lock in the code
if process_clicked:
    st.session_state.active_code = code

active_code = st.session_state.active_code

# Wait until we have an active code
if active_code is not None:

    # ----------------- Load data -----------------
    table, summary, meta = load_payload(DATA_DIR, active_code)

    # BigQuery data for the chart
    client = get_bigquery_client(PROJECT_ID)
    df_all, df_quarter = get_all_and_quarterly(active_code, client)

    # Header
    st.header(meta.get("company", ""))
    st.subheader(meta.get("period_label", ""))

    # ----------------- Create pages (tabs) -----------------
    tabs = st.tabs(["Outlook", "Stats", "Money Flow"])

    # --- TAB 1: Sankey Diagram --------------------------------------
    with tabs[0]:
        # st.markdown("---")
        st.subheader("Fundamental Summary")
        commentary_and_snapshot(summary, meta)
        
        st.markdown("---")
        st.subheader("Revenue Breakdown")
        sankey_section(active_code)

    # --- TAB 2: Fundamental Summary ---------------------------------
    with tabs[1]:
        # st.markdown("---")
        quarterly_fundamental_chart(active_code, df_quarter)

        
        suggestion = load_investment_suggestion_json(active_code, output_dir=Path("output/code_analysis"))
        if suggestion is None:
            st.info("No investment suggestion JSON found for this ticker yet.")
        else:
            render_investment_suggestion(suggestion)

        st.markdown("---")
        st.subheader('Important Metrics')

        render_core_fundamental_table(active_code, df_all)

        st.markdown("---")
        

        

    # --- TAB 3: Money Flow ------------------------------------------
    with tabs[2]:
        st.subheader("Money Flow")
        st.info("This section will visualize internal money flows (coming soon).")
