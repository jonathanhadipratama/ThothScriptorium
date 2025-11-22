# app.py — Airbnb-inspired income statement explorer

from pathlib import Path

import streamlit as st

from src.plot_sankey import plot_income_sankey  # still imported if you need directly
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
CODES = ["ULTJ", "MYOR", "CMRY", "UNVR", 'INDF', 'ICBP', "KEJU", "DMND", "GOOD"]

# ----------------- Theme -----------------
load_theme_css()

# ----------------- Hero + ticker selection -----------------
code = hero_section(CODES)

# ----------------- Load data -----------------
table, summary, meta = load_payload(DATA_DIR, code)

# ----------------- Main sections -----------------
sankey_section(code)
commentary_and_snapshot(summary, meta)
raw_table_section(table)
