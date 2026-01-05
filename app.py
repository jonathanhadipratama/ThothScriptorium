import streamlit as st
from dotenv import load_dotenv
from src.ui.time_section import week_counter_2026_section

load_dotenv()

# st.set_page_config(page_title="Streamlit Template", layout="wide")

# ----------------- Page config -----------------
st.set_page_config(
    page_title="Thoth Scriptorium",
    page_icon="🪶",
    layout="wide",
)

# --- Sidebar logo (TOP) ---
with st.sidebar:
    st.image(
        "assets/logo.png",
        width='stretch',
    )

    week_counter_2026_section()


# --- Pages ---
foreign_flow = st.Page("foreignflow.py", title="Screener", icon=":material/airwave:", default=True)
comp_profile = st.Page('company_profile.py', title="Company Profile", icon=":material/dashboard:")


pg = st.navigation(
    {"Reports": [foreign_flow, comp_profile]}
)

pg.run()
