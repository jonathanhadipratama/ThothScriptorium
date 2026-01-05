import pandas as pd
import streamlit as st
from src.data_extraction import get_screener_minervini


# ---------- Styling helpers ----------

def _color_bool(val):
    if isinstance(val, bool):
        return (
            "background-color: #d4f8d4; color: #145214"
            if val
            else "background-color: #f8d4d4; color: #7a0c0c"
        )
    return ""


def _style_minervini_dataframe(df: pd.DataFrame):
    styled_df = df.copy()

    num_cols = styled_df.select_dtypes(include=["int64", "float64"]).columns
    bool_cols = styled_df.select_dtypes(include=["bool"]).columns

    def format_number(val):
        if pd.isna(val):
            return val
        if isinstance(val, (int, float)) and val == int(val):
            return f"{int(val):,}"
        return f"{val:,.2f}"

    return (
        styled_df.style
        .format({col: format_number for col in num_cols})
        .applymap(_color_bool, subset=bool_cols)
    )


# ---------- Public render function ----------

def render_minervini_table(height: int = 520):
    """
    Render Minervini screener table with:
    - Green/red boolean highlighting
    - Numeric formatting
    - Streamlit-native dataframe

    Usage:
        from src.plot_minervini_table import render_minervini_table
        render_minervini_table()
    """
    try:
        df = get_screener_minervini()

        if df.empty:
            st.warning("Minervini screener returned no data.")
            return

        st.caption(f"Rows shown: {len(df):,}")

        st.dataframe(
            _style_minervini_dataframe(df),
            use_container_width=True,
            height=height
        )

    except Exception as e:
        st.error(f"Failed to load Minervini screener: {e}")
