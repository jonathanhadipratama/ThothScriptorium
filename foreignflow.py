import pandas as pd
import streamlit as st
from pathlib import Path
from src.ui.components import hero_header
from src.ui.theme import load_theme_css
from src.plot_scatter import render_scatter
from src.data_extraction import get_sector_flow, get_stock_flow

load_theme_css()
st.set_page_config(page_title="Foreign Flow", layout="wide")
hero_header()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "flow"
SECTOR_PATH = DATA_DIR / "sector_flow.csv"
STOCK_PATH = DATA_DIR / "stock_flow.csv"


@st.cache_data(show_spinner=False)
def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return pd.read_csv(path)


def style_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply formatting to numeric columns while keeping them sortable.
    Returns a styled dataframe.
    """
    # Create a copy to avoid modifying original
    styled_df = df.copy()
    
    # Get numeric columns
    num_cols = styled_df.select_dtypes(include=["int64", "float64"]).columns
    
    # Apply Styler formatting
    def format_number(val):
        if pd.isna(val):
            return val
        # Check if it's an integer-like value
        if isinstance(val, (int, float)) and val == int(val):
            return f"{int(val):,}"
        else:
            return f"{val:,.2f}"
    
    styler = styled_df.style.format({col: format_number for col in num_cols})
    return styler

render_scatter()

st.title("Foreign Flow")

# ---- Sector Flow (with min threshold filter) ----
st.header("Sector Flow (All)")

try:
    
    sector_df = get_sector_flow()
    target_col = "positive_net_ratio_10d"
    
    if target_col not in sector_df.columns:
        st.error(f'sector_flow dataset must contain a "{target_col}" column.')
    else:
        # Ensure numeric for filtering
        sector_df[target_col] = pd.to_numeric(sector_df[target_col], errors="coerce")
        
        # Get min/max for slider
        col_min = float(sector_df[target_col].min(skipna=True))
        col_max = float(sector_df[target_col].max(skipna=True))
        
        # Fallback if column is all NaN
        if pd.isna(col_min) or pd.isna(col_max):
            st.warning(f'"{target_col}" has no valid numeric values; showing all rows.')
            filtered_sector = sector_df
        else:
            min_threshold = st.slider(
                f"Minimum {target_col}",
                min_value=float(col_min),
                max_value=float(col_max),
                value=float(col_min),
                step=0.1
            )
            filtered_sector = sector_df[sector_df[target_col] >= min_threshold]
        
        st.caption(f"Rows shown: {len(filtered_sector):,} / {len(sector_df):,}")
        
        # Display with styling
        st.dataframe(
            style_dataframe(filtered_sector),
            width='stretch',
            height=420
        )

except Exception as e:
    st.error(f"Failed to load sector_flow.csv: {e}")

st.divider()

# ---- Stock Flow (filter by sector) ----
st.header("Stock Flow (Filter by Sector)")

try:
    stock_df = get_stock_flow()
    
    if "sector" not in stock_df.columns:
        st.error('stock_flow dataset must contain a "sector" column.')
    else:
        sectors = sorted(
            stock_df["sector"]
            .dropna()
            .astype(str)
            .unique()
            .tolist(),
            key=str.lower
        )
        options = ["All"] + sectors
        selected = st.selectbox("Select sector", options)
        
        if selected != "All":
            filtered_df = stock_df[stock_df["sector"].astype(str) == selected]
        else:
            filtered_df = stock_df
        
        st.caption(f"Rows shown: {len(filtered_df):,} / {len(stock_df):,}")
        
        # Display with styling
        st.dataframe(
            style_dataframe(filtered_df),
            use_container_width=True,
            height=520
        )

except Exception as e:
    st.error(f"Failed to load stock_flow.csv: {e}")