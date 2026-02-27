import pandas as pd
import streamlit as st
from pathlib import Path
from src.ui.components import hero_header
from src.ui.theme import load_theme_css
from src.plot_scatter import render_scatter
from src.data_extraction import get_sector_flow, get_stock_flow, get_sector_flow_7d_vs_30d, get_stock_flow_7d_vs_30d
from src.plot_minervini_table import render_minervini_table

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


def apply_price_return_filters(df: pd.DataFrame, key_prefix: str) -> pd.DataFrame:
    """Render a range slider for every column whose name contains 'return' and filter df."""
    return_cols = [c for c in df.columns if "return" in c.lower()]
    if not return_cols:
        return df

    filtered = df.copy()
    slider_cols = st.columns(len(return_cols))
    for i, col in enumerate(return_cols):
        series = pd.to_numeric(filtered[col], errors="coerce")
        col_min = float(series.min(skipna=True))
        col_max = float(series.max(skipna=True))
        if pd.isna(col_min) or pd.isna(col_max) or col_min == col_max:
            continue
        lo, hi = slider_cols[i].slider(
            col,
            min_value=col_min,
            max_value=col_max,
            value=(col_min, col_max),
            step=0.01,
            key=f"{key_prefix}_{col}",
        )
        filtered = filtered[pd.to_numeric(filtered[col], errors="coerce").between(lo, hi)]
    return filtered


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
            style_dataframe(filtered_sector.sort_values('positive_net_ratio_10d', ascending = False)),
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
            style_dataframe(filtered_df.sort_values('positive_net_ratio_10d', ascending = False)),
            use_container_width=True,
            height=520
        )

except Exception as e:
    st.error(f"Failed to load stock_flow.csv: {e}")

st.divider()

# ---- Sector Flow 7D vs 30D ----
st.header("Sector Flow: 7D vs 30D")

try:
    flow_7d_30d_df = get_sector_flow_7d_vs_30d()

    if flow_7d_30d_df.empty:
        st.warning("No data returned from v_sector_flow_7d_vs_30d.")
    else:
        if "flow_signal" in flow_7d_30d_df.columns:
            signals = sorted(
                flow_7d_30d_df["flow_signal"].dropna().astype(str).unique().tolist(),
                key=str.lower,
            )
            selected_signals = st.multiselect("Filter by flow_signal", signals, default=signals, key="sector_flow_signal")
            if selected_signals:
                filtered_flow = flow_7d_30d_df[
                    flow_7d_30d_df["flow_signal"].astype(str).isin(selected_signals)
                ]
            else:
                filtered_flow = flow_7d_30d_df
        else:
            st.warning('"flow_signal" column not found; showing all rows.')
            filtered_flow = flow_7d_30d_df

        filtered_flow = apply_price_return_filters(filtered_flow, key_prefix="sector_7d30d")

        st.caption(f"Rows shown: {len(filtered_flow):,} / {len(flow_7d_30d_df):,}")
        st.dataframe(
            style_dataframe(filtered_flow),
            use_container_width=True,
            height=520,
        )

except Exception as e:
    st.error(f"Failed to load sector flow 7d vs 30d: {e}")

st.divider()

# ---- Stock Flow 7D vs 30D ----
st.header("Stock Flow: 7D vs 30D")

try:
    stock_7d_30d_df = get_stock_flow_7d_vs_30d()

    if stock_7d_30d_df.empty:
        st.warning("No data returned from v_stock_flow_7d_vs_30d.")
    else:
        filter_col1, filter_col2 = st.columns(2)

        if "flow_signal" in stock_7d_30d_df.columns:
            signals = sorted(
                stock_7d_30d_df["flow_signal"].dropna().astype(str).unique().tolist(),
                key=str.lower,
            )
            selected_signals = filter_col1.multiselect("Filter by flow_signal", signals, default=signals, key="stock_flow_signal")
        else:
            selected_signals = []

        if "sector" in stock_7d_30d_df.columns:
            sectors = sorted(
                stock_7d_30d_df["sector"].dropna().astype(str).unique().tolist(),
                key=str.lower,
            )
            selected_sector = filter_col2.selectbox("Filter by sector", ["All"] + sectors, key="stock_7d30d_sector")
        else:
            selected_sector = "All"

        filtered_stock_flow = stock_7d_30d_df
        if selected_signals:
            filtered_stock_flow = filtered_stock_flow[
                filtered_stock_flow["flow_signal"].astype(str).isin(selected_signals)
            ]
        if selected_sector != "All":
            filtered_stock_flow = filtered_stock_flow[
                filtered_stock_flow["sector"].astype(str) == selected_sector
            ]

        filtered_stock_flow = apply_price_return_filters(filtered_stock_flow, key_prefix="stock_7d30d")

        st.caption(f"Rows shown: {len(filtered_stock_flow):,} / {len(stock_7d_30d_df):,}")
        st.dataframe(
            style_dataframe(filtered_stock_flow),
            use_container_width=True,
            height=520,
        )

except Exception as e:
    st.error(f"Failed to load stock flow 7d vs 30d: {e}")

st.divider()
st.header("Minervini Screener")
render_minervini_table()