import streamlit as st
import pandas as pd
from data_extraction import *

code = "CMRY"

client = get_bigquery_client(PROJECT_ID)

df_all, df_quarter = get_all_and_quarterly(code, client)

category = df_all[(df_all['metric']=='market_cap')&
                     (df_all['code']!=code)][['code','clean_value']]\
                            .drop_duplicates().sort_values('clean_value', ascending = False).head(5)['code'].unique()

category = [code] + list(category)

df_all_filtered = df_all[df_all['code'].isin(category)][['code','metric','clean_value']].drop_duplicates()
df = df_all_filtered.pivot(index = 'metric', columns = 'code', values = 'clean_value')

core_metrics_in_order = [
    # QUALITY
    "Return On Invested Capital (TTM)",   # ROIC
    "Return on Equity (TTM)",             # ROE
    "Operating Profit Margin (Quarter)",
    "Current EPS (TTM)",                  # using this as EPS (TTM)

    # GROWTH
    "Revenue (Quarter YoY Growth)",
    "EPS Growth (TTM)",                   # if not in df, will be skipped
    "Net Income (Quarter YoY Growth)",

    # CASH FLOW
    "Cash From Operations (TTM)",
    "Free cash flow (TTM)",
    "Free Cashflow Per Share (TTM)",

    # RISK / BALANCE SHEET
    "Debt to Equity Ratio (Quarter)",
    "Interest Coverage (TTM)",
    "Net Debt (Quarter)",
    "Current Ratio (Quarter)",
    "Altman Z-Score (Modified)",

    # EFFICIENCY / OPERATIONS
    "Asset Turnover (TTM)",
    "Cash Conversion Cycle (Quarter)",
    "Inventory Turnover (TTM)",

    # VALUATION
    "Current PE Ratio (TTM)",
    "PEG Ratio",
]

# Keep only metrics that actually exist in the DataFrame,
# but preserve the intended order:
metrics_available = [m for m in core_metrics_in_order if m in df.index]

df_core = df.loc[metrics_available].copy()

# -------------------------------------------------------------------
# 2. Map each metric to a segment for highlighting
# -------------------------------------------------------------------
metric_to_segment = {
    # QUALITY
    "Return On Invested Capital (TTM)": "Quality",
    "Return on Equity (TTM)": "Quality",
    "Operating Profit Margin (Quarter)": "Quality",
    "Current EPS (TTM)": "Quality",

    # GROWTH
    "Revenue (Quarter YoY Growth)": "Growth",
    "EPS Growth (TTM)": "Growth",
    "Net Income (Quarter YoY Growth)": "Growth",

    # CASH FLOW
    "Cash From Operations (TTM)": "Cash Flow",
    "Free cash flow (TTM)": "Cash Flow",
    "Free Cashflow Per Share (TTM)": "Cash Flow",

    # RISK
    "Debt to Equity Ratio (Quarter)": "Risk",
    "Interest Coverage (TTM)": "Risk",
    "Net Debt (Quarter)": "Risk",
    "Current Ratio (Quarter)": "Risk",
    "Altman Z-Score (Modified)": "Risk",

    # EFFICIENCY
    "Asset Turnover (TTM)": "Efficiency",
    "Cash Conversion Cycle (Quarter)": "Efficiency",
    "Inventory Turnover (TTM)": "Efficiency",

    # VALUATION
    "Current PE Ratio (TTM)": "Valuation",
    "PEG Ratio": "Valuation",
}

segment_colors = {
    "Quality":   "#FFFFFF",
    "Growth":    "#E1F5F8",
    "Cash Flow": "#FFFFFF",
    "Risk":      "#E1F5F8",
    "Efficiency":"#FFFFFF",
    "Valuation": "#E1F5F8"
    "",
}

# -------------------------------------------------------------------
# 3. Formatting function for big numbers (K, M, B, T)
# -------------------------------------------------------------------
def human_format(x):
    """Format numbers into K / M / B / T, keep small numbers as decimals."""
    if pd.isna(x):
        return ""
    # If it's not a number, just return as is
    if not isinstance(x, (int, float)):
        return x

    abs_x = abs(x)

    if abs_x >= 1e12:
        return f"{x / 1e12:.2f}T"
    elif abs_x >= 1e9:
        return f"{x / 1e9:.2f}B"
    elif abs_x >= 1e6:
        return f"{x / 1e6:.2f}M"
    elif abs_x >= 1e3:
        return f"{x / 1e3:.2f}K"
    else:
        # for ratios/percents like 0.24, 0.05, etc.
        return f"{x:.4f}".rstrip("0").rstrip(".")  # tidy up trailing zeros

# -------------------------------------------------------------------
# 4. Row-wise style function to highlight segments
# -------------------------------------------------------------------
def highlight_segments(row):
    metric = row.name
    segment = metric_to_segment.get(metric, None)
    color = segment_colors.get(segment, "")
    if color:
        return [f"background-color: {color}" for _ in row]
    else:
        return ["" for _ in row]

# -------------------------------------------------------------------
# 5. Build the Styler with formatting + segment highlighting
# -------------------------------------------------------------------
styled = (
    df_core
    .style
    .format(human_format)
    .apply(highlight_segments, axis=1)
)

# -------------------------------------------------------------------
# 6. Streamlit view
# -------------------------------------------------------------------
st.set_page_config(layout="wide")
st.title("Core Fundamental Metrics – FMCG Stocks")

# st.markdown(
#     """
#     This table shows the **20 core metrics** grouped by segment:

#     - 🟨 **Quality** (ROIC, ROE, margins, EPS)  
#     - 🟦 **Growth** (Revenue & Net Income YoY, EPS growth if available)  
#     - 🟩 **Cash Flow** (CFO, FCF, FCF per share)  
#     - 🟥 **Risk** (D/E, interest coverage, net debt, liquidity, Z-score)  
#     - ⬜ **Efficiency** (asset & working capital efficiency)  
#     - 🔵 **Valuation** (PE & PEG)  

#     Large numbers (revenue, cash flow, debt, etc.) are shown in **K / M / B / T** to keep it readable.
#     """
# )

# Streamlit supports Styler directly; if your version doesn't, fall back to st.write with HTML.
st.dataframe(styled, use_container_width=True)
# If st.dataframe(styled) doesn't work in your environment, use:
# st.write(styled.to_html(), unsafe_allow_html=True)
