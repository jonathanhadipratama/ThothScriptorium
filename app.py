import streamlit as st

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
        use_container_width=True,
    )


# --- Pages ---
comp_profile = st.Page('company_profile.py', title="Dashboard", icon=":material/dashboard:", default=True)
foreign_flow = st.Page("foreignflow.py", title="Bug reports", icon=":material/airwave:")

pg = st.navigation(
    {"Reports": [comp_profile, foreign_flow],}
)

pg.run()
