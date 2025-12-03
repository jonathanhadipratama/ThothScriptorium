from pathlib import Path
import streamlit as st

from src.ui.theme import load_theme_css
from src.ui.components import (
    hero_section,
    load_payload,
    sankey_section,
    commentary_and_snapshot,
    raw_table_section,
)
from src.ui.fundamental_chart import quarterly_fundamental_chart
from src.data_extraction import get_bigquery_client, get_all_and_quarterly, PROJECT_ID

# ----------------- Page config -----------------
st.set_page_config(
    page_title="Thoth Scriptorium",
    page_icon="🪶",
    layout="wide",
)

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

    # ----------------- Create pages (tabs) -----------------
    tabs = st.tabs(["Fundamental Summary", "Sankey Diagram", "Money Flow"])

    # --- TAB 1: Fundamental Summary ---------------------------------
    with tabs[0]:

        st.markdown("---")
        quarterly_fundamental_chart(active_code, df_quarter)

        st.markdown("---")
        st.subheader("Fundamental Summary")
        commentary_and_snapshot(summary, meta)

        

    # --- TAB 2: Sankey Diagram --------------------------------------
    with tabs[1]:
        sankey_section(active_code)

    # --- TAB 3: Money Flow ------------------------------------------
    with tabs[2]:
        st.subheader("Money Flow")
        st.info("This section will visualize internal money flows (coming soon).")
