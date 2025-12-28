import streamlit as st
import pandas as pd
from typing import List, Tuple


def human_format(x):
    """
    Format numbers into K / M / B / T, keep small numbers as decimals.
    For small decimals, keep only two digits after the decimal point.
    """
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
        # Two digits after decimal for small numbers
        return f"{x:.2f}".rstrip("0").rstrip(".")



def _extract_core_fundamental_df(
    code: str, df_all: pd.DataFrame
) -> Tuple[pd.DataFrame | None, str | None]:
    """
    Extract and shape the core fundamental data into a plain dataframe:
      Segment | Metric | <code> | <peers...>
    Returns:
      - df_core (plain DataFrame) if success, else None
      - warning message if failed, else None
    """

    # Compute competitor list based on market cap ----
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

    # Take top x competitors
    competitors_sorted = competitors_sorted[:10]

    # Final column order: selected code FIRST, then competitors (in market-cap order)
    final_cols: List[str] = [code] + competitors_sorted

    # Build pivot table: metric x code ----
    df_filtered = (
        df_all[df_all["code"].isin(final_cols)][["code", "metric", "clean_value"]]
        .drop_duplicates()
    )

    if df_filtered.empty:
        return None, "No data available for this stock."

    df = df_filtered.pivot(index="metric", columns="code", values="clean_value")

    # Ensure final column order inside pivot (skip any that might not exist)
    df = df[[c for c in final_cols if c in df.columns]]

    # Keep only core metrics, in desired group order ----
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
        return None, "No core metrics available for this stock."

    df_core = df.loc[metrics_available].copy()

    # Add Segment + move Metric to a column ----
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

    df_core["Segment"] = [metric_to_segment.get(m, "") for m in df_core.index]

    df_core = df_core.reset_index()
    df_core.rename(columns={"metric": "Metric"}, inplace=True)

    # Desired column order
    col_order = ["Segment", "Metric"] + [c for c in final_cols if c in df_core.columns]
    df_core = df_core[col_order]

    return df_core, None

# Styling
def _style_core_fundamental_df(df_core: pd.DataFrame) -> pd.io.formats.style.Styler:
    """
    Apply formatting + row highlight to the already-shaped df_core.
    No data logic here—only styling.
    """

    segment_colors = {
        "Quality":    "#FFFFFF",
        "Growth":     "#E1F5F8",
        "Cash Flow":  "#FFFFFF",
        "Risk":       "#E1F5F8",
        "Efficiency": "#FFFFFF",
        "Valuation":  "#E1F5F8",
    }

    def highlight_row(row):
        segment = row["Segment"]
        color = segment_colors.get(segment, "")
        if color:
            return [f"background-color: {color}"] * len(row)
        else:
            return [""] * len(row)

    numeric_cols = [c for c in df_core.columns if c not in ("Segment", "Metric")]

    return (
        df_core.style
        .format(human_format, subset=numeric_cols)
        .apply(highlight_row, axis=1)
    )


# Rendering
def _render_core_fundamental_table_ui(code: str, styled) -> None:
    st.caption(f"Core fundamental metrics - {code} vs peers")
    st.dataframe(styled, use_container_width=True, height=600)


# End function
def render_core_fundamental_table(code: str, df_all: pd.DataFrame) -> None:
    df_core, warning_msg = _extract_core_fundamental_df(code, df_all)
    if warning_msg:
        st.warning(warning_msg)
        return

    styled = _style_core_fundamental_df(df_core)
    _render_core_fundamental_table_ui(code, styled)
