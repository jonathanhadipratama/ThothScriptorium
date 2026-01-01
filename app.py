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
foreign_flow = st.Page("foreignflow.py", title="Foreign Flow", icon=":material/airwave:", default=True)
comp_profile = st.Page('company_profile.py', title="Company Profile", icon=":material/dashboard:")


pg = st.navigation(
    {"Reports": [foreign_flow, comp_profile]}
)

pg.run()
