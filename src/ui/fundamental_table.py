import streamlit as st
import pandas as pd
from typing import List


def human_format(x):
    """Format numbers into K / M / B / T, keep small numbers as decimals."""
    if pd.isna(x):
        return ""
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
        return f"{x:.4f}".rstrip("0").rstrip(".")


def render_core_fundamental_table(code: str, df_all: pd.DataFrame) -> None:
    """
    Render the core fundamental table for the given stock code.
    Uses df_all that has already been fetched (no extra queries).
    """

    # ---- 1. Compute competitor list based on market cap ----
    df_market = (
        df_all[(df_all["metric"] == "market_cap") & (df_all["code"] != code)]
        [["code", "clean_value"]]
        .drop_duplicates()
    )

    competitors_sorted = (
        df_market.sort_values("clean_value", ascending=False)["code"]
        .unique()
        .tolist()
    )

    # Take top 5 competitors
    competitors_sorted = competitors_sorted[:5]

    # Final column order: selected code FIRST, then competitors (in market-cap order)
    final_cols: List[str] = [code] + competitors_sorted

    # ---- 2. Build pivot table: metric x code ----
    df_filtered = (
        df_all[df_all["code"].isin(final_cols)][["code", "metric", "clean_value"]]
        .drop_duplicates()
    )

    if df_filtered.empty:
        st.warning("No data available for this stock.")
        return

    df = df_filtered.pivot(index="metric", columns="code", values="clean_value")

    # Ensure final column order inside pivot (skip any that might not exist)
    df = df[[c for c in final_cols if c in df.columns]]

    # ---- 3. Keep only core metrics, in desired group order ----
    core_metrics_in_order = [
        # QUALITY
        "Return On Invested Capital (TTM)",
        "Return on Equity (TTM)",
        "Operating Profit Margin (Quarter)",
        "Current EPS (TTM)",

        # GROWTH
        "Revenue (Quarter YoY Growth)",
        "EPS Growth (TTM)",
        "Net Income (Quarter YoY Growth)",

        # CASH FLOW
        "Cash From Operations (TTM)",
        "Free cash flow (TTM)",
        "Free Cashflow Per Share (TTM)",

        # RISK
        "Debt to Equity Ratio (Quarter)",
        "Interest Coverage (TTM)",
        "Net Debt (Quarter)",
        "Current Ratio (Quarter)",
        "Altman Z-Score (Modified)",

        # EFFICIENCY
        "Asset Turnover (TTM)",
        "Cash Conversion Cycle (Quarter)",
        "Inventory Turnover (TTM)",

        # VALUATION
        "Current PE Ratio (TTM)",
        "PEG Ratio",
    ]

    metrics_available = [m for m in core_metrics_in_order if m in df.index]

    if not metrics_available:
        st.warning("No core metrics available for this stock.")
        return

    df_core = df.loc[metrics_available].copy()

    # ---- 4. Segment color mapping + add Segment column ----
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
        "Valuation": "#E1F5F8",
    }

    # Add Segment column based on metric index
    df_core["Segment"] = [metric_to_segment.get(m, "") for m in df_core.index]

    # Move metric out of index into a real column "Metric"
    df_core = df_core.reset_index()
    df_core.rename(columns={"metric": "Metric"}, inplace=True)

    # Desired column order in the table:
    # Segment | Metric | <selected code> | <competitors...>
    col_order = ["Segment", "Metric"] + [c for c in final_cols if c in df_core.columns]
    df_core = df_core[col_order]

    # ---- 5. Row-wise highlight: color ENTIRE row including Segment + Metric ----
    def highlight_row(row):
        segment = row["Segment"]
        color = segment_colors.get(segment, "")
        if color:
            return [f"background-color: {color}"] * len(row)
        else:
            return [""] * len(row)

    # Only format numeric columns (the tickers); Segment & Metric stay as text
    numeric_cols = [c for c in df_core.columns if c not in ("Segment", "Metric")]

    styled = (
        df_core
        .style
        .format(human_format, subset=numeric_cols)
        .apply(highlight_row, axis=1)
    )

    # ---- 6. Render inside a themed card so it matches the app ----
    table_html = styled.to_html()

    st.markdown(
        f"""
        <div class="card-light" style="margin-top: 1.2rem;">
            <div class="card-title">
                Core fundamental metrics – peers vs <b>{code}</b>
            </div>
            {table_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
