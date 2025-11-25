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

# ----------------- Hero + ticker selection -----------------
code, process_clicked = hero_section(CODES)

# Wait until user clicks the button
if process_clicked:

    # ----------------- Load data -----------------
    table, summary, meta = load_payload(DATA_DIR, code)

    # ----------------- Create pages (tabs) -----------------
    tabs = st.tabs(["Fundamental Summary", "Sankey Diagram", "Money Flow"])

    # --- TAB 1: Fundamental Summary ---------------------------------
    with tabs[0]:
        st.subheader("Fundamental Summary")
        st.info("This section will contain the company's fundamental analysis summary.")
        commentary_and_snapshot(summary, meta)

    # --- TAB 2: Sankey Diagram --------------------------------------
    with tabs[1]:
        sankey_section(code)
        # raw_table_section(table)

    # --- TAB 3: Money Flow ------------------------------------------
    with tabs[2]:
        st.subheader("Money Flow")
        st.info("This section will visualize internal money flows (coming soon).")
