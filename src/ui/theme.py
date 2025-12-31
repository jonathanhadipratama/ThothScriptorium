from pathlib import Path
import streamlit as st

def load_theme_css(path: str = "assets/theme.css") -> None:
    css = Path(path).read_text(encoding="utf-8")

    sidebar_nav_css = """
    /* --- Minimal black & white sidebar navigation --- */
[data-testid="stSidebar"] {
    padding-top: 1rem;
}

.sidebar-nav {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    margin-top: 0.25rem;
}

.sidebar-nav a {
    text-decoration: none !important;
}

.sidebar-nav .nav-item {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.6rem 0.75rem;
    border-radius: 10px;
    font-weight: 600;
    font-size: 0.95rem;

    background: #ffffff;
    color: #111111;
    border: 1px solid rgba(0, 0, 0, 0.08);

    transition: all 120ms ease;
}

.sidebar-nav .nav-item:hover {
    background: #f5f5f5;
    border-color: rgba(0, 0, 0, 0.18);
}

.sidebar-nav .nav-item.active {
    background: #111111;
    color: #ffffff;
    border-color: #111111;
}

.sidebar-nav .nav-icon {
    width: 1.4rem;
    display: inline-flex;
    justify-content: center;
}

    """

    st.markdown(
        f"""
        <style>
        {css}

        {sidebar_nav_css}
        </style>
        """,
        unsafe_allow_html=True,
    )
