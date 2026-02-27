"""
Foreign Money Flow Explorer — Standalone Visualization
=======================================================
Run with:  streamlit run foreign_flow_viz.py

Two-level drill-down:
  1. Sector overview  → Treemap + Quadrant Scatter
  2. Stock deep-dive  → Flow Scatter + Ranking Bar (per selected sector)

Data sources:
  data/flow/sector_flow.csv   – one row per sector
  data/flow/stock_flow.csv    – one row per stock
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path


# ─────────────────────────────────────────────────────────
# App config
# ─────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Foreign Flow Explorer",
    layout="wide",
    page_icon="💹",
)

BASE_DIR   = Path(__file__).resolve().parent
SECTOR_CSV = BASE_DIR / "data" / "flow" / "sector_flow.csv"
STOCK_CSV  = BASE_DIR / "data" / "flow" / "stock_flow.csv"

PHASE_COLORS = {
    "Accumulation": "#10B981",   # emerald
    "Distribution": "#EF4444",   # red
    "Neutral":      "#94A3B8",   # slate
}

TEAL    = "#0D9488"
BG      = "#F5F6FA"
PLOT_BG = "#FFFFFF"


# ─────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_sector() -> pd.DataFrame:
    df = pd.read_csv(SECTOR_CSV)
    df["flow_size"]        = df["ma10_slope"].abs()          # treemap / bubble size
    df["sub_sector_label"] = df["sub_sector"].str.title()    # display name
    # Ensure price_return_10d is numeric
    df["price_return_10d"] = pd.to_numeric(df["price_return_10d"], errors="coerce")
    df["positive_net_ratio_10d"] = pd.to_numeric(df["positive_net_ratio_10d"], errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def load_stocks() -> pd.DataFrame:
    df = pd.read_csv(STOCK_CSV)
    # price_return_10d in stock_flow is a decimal (e.g. 0.058 = 5.8%) → convert to %
    df["price_return_pct"]       = pd.to_numeric(df["price_return_10d"], errors="coerce") * 100
    df["positive_net_ratio_10d"] = pd.to_numeric(df["positive_net_ratio_10d"], errors="coerce")
    df["cumsumnetvalue_ma10"]    = pd.to_numeric(df["cumsumnetvalue_ma10"], errors="coerce")
    df["foreign_percentage"]     = pd.to_numeric(df["foreign_percentage"], errors="coerce")
    # Clamp foreign_percentage for bubble size (avoid zero-size)
    df["bubble_size"] = df["foreign_percentage"].clip(lower=1)
    return df


# ─────────────────────────────────────────────────────────
# Sector-level figures
# ─────────────────────────────────────────────────────────

def fig_treemap(df: pd.DataFrame) -> go.Figure:
    """Treemap: sector boxes sized by absolute net flow, colored by phase."""
    fig = px.treemap(
        df,
        path=["flow_phase", "sub_sector_label"],
        values="flow_size",
        color="flow_phase",
        color_discrete_map=PHASE_COLORS,
        custom_data=["positive_net_ratio_10d", "price_return_10d", "flow_phase"],
        title="Sector Foreign Flow — Treemap",
    )
    fig.update_traces(
        texttemplate="<b>%{label}</b>",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Phase: %{customdata[2]}<br>"
            "Pos-day ratio: %{customdata[0]:.0%}<br>"
            "10d price return: %{customdata[1]:+.2f}%<br>"
            "Net flow size: %{value:,.0f}<br>"
            "<extra></extra>"
        ),
    )
    fig.update_layout(
        height=480,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor=BG,
    )
    return fig


def fig_sector_quadrant(df: pd.DataFrame) -> go.Figure:
    """
    Quadrant scatter:
      X = positive_net_ratio_10d  (flow momentum, 0–1)
      Y = price_return_10d        (% price change)
      size = abs(ma10_slope)
      color = flow_phase
    """
    y_pad = max(abs(df["price_return_10d"].max()), abs(df["price_return_10d"].min())) * 1.25

    fig = px.scatter(
        df,
        x="positive_net_ratio_10d",
        y="price_return_10d",
        size="flow_size",
        color="flow_phase",
        color_discrete_map=PHASE_COLORS,
        text="sub_sector_label",
        hover_name="sub_sector_label",
        hover_data={
            "flow_phase":             True,
            "positive_net_ratio_10d": ":.2f",
            "price_return_10d":       ":.2f",
            "flow_size":              False,
            "sub_sector_label":       False,
        },
        size_max=45,
        title="Sector Flow Quadrant — Flow Momentum vs 10d Price Return",
    )

    fig.update_traces(
        textposition="top center",
        textfont=dict(size=9, color="#1E293B"),
        marker=dict(opacity=0.80, line=dict(width=1, color="white")),
    )

    # Quadrant dividers
    fig.add_vline(x=0.5, line_dash="dot", line_color="#CBD5E1", line_width=1.5)
    fig.add_hline(y=0.0, line_dash="dot", line_color="#CBD5E1", line_width=1.5)

    ann_kw = dict(showarrow=False, font=dict(size=10, color="#94A3B8"))
    fig.add_annotation(x=0.78, y= y_pad * 0.88, text="Buying + Rising",   **ann_kw)
    fig.add_annotation(x=0.22, y= y_pad * 0.88, text="Rising, Weak Flow", **ann_kw)
    fig.add_annotation(x=0.78, y=-y_pad * 0.88, text="Flow In, Lagging",  **ann_kw)
    fig.add_annotation(x=0.22, y=-y_pad * 0.88, text="Selling + Falling", **ann_kw)

    fig.update_xaxes(title="Positive Net Flow Ratio (10d)", range=[0, 1])
    fig.update_yaxes(title="Price Return 10d (%)", range=[-y_pad, y_pad])
    fig.update_layout(
        height=580,
        margin=dict(l=40, r=40, t=60, b=40),
        paper_bgcolor=BG,
        plot_bgcolor=PLOT_BG,
        legend_title_text="Phase",
    )
    return fig


# ─────────────────────────────────────────────────────────
# Stock-level figures
# ─────────────────────────────────────────────────────────

def fig_stock_scatter(df: pd.DataFrame, sector: str) -> go.Figure:
    """
    Scatter for stocks in a sector:
      X = positive_net_ratio_10d
      Y = price_return_pct   (converted to %)
      size = foreign_percentage
      color = cumsumnetvalue_ma10  (diverging: red=outflow, green=inflow)
    """
    vmax = df["cumsumnetvalue_ma10"].abs().max()
    if vmax == 0:
        vmax = 1  # avoid divide-by-zero

    fig = px.scatter(
        df,
        x="positive_net_ratio_10d",
        y="price_return_pct",
        size="bubble_size",
        color="cumsumnetvalue_ma10",
        color_continuous_scale="RdYlGn",
        range_color=[-vmax, vmax],
        text="stockcode",
        hover_name="stockcode",
        hover_data={
            "sector":                 False,
            "foreign_percentage":     ":.1f",
            "price_return_pct":       ":.2f",
            "cumsumnetvalue_ma10":    ":,.0f",
            "positive_net_ratio_10d": ":.2f",
            "stockcode":              False,
            "bubble_size":            False,
        },
        size_max=40,
        title=f"Stock Flow — {sector}  |  bubble size = foreign %  |  color = cumulative net flow",
    )

    fig.update_traces(
        textposition="top center",
        textfont=dict(size=8, color="#1E293B"),
        marker=dict(opacity=0.85, line=dict(width=0.5, color="white")),
    )

    y_vals  = df["price_return_pct"].dropna()
    y_pad   = max(abs(y_vals.max()), abs(y_vals.min()), 0.5) * 1.3

    fig.add_vline(x=0.5, line_dash="dot", line_color="#CBD5E1", line_width=1.5)
    fig.add_hline(y=0.0, line_dash="dot", line_color="#CBD5E1", line_width=1.5)

    fig.update_xaxes(title="Positive Net Flow Ratio (10d)", range=[0, 1])
    fig.update_yaxes(title="Price Return 10d (%)", range=[-y_pad, y_pad])
    fig.update_coloraxes(
        colorbar_title="Cum. Net Flow",
        colorbar_tickformat=".2s",
    )
    fig.update_layout(
        height=560,
        margin=dict(l=40, r=40, t=60, b=40),
        paper_bgcolor=BG,
        plot_bgcolor=PLOT_BG,
    )
    return fig


def fig_stock_bar(df: pd.DataFrame, sector: str) -> go.Figure:
    """
    Horizontal bar ranked by positive_net_ratio_10d.
    Bar color: green if cumsumnetvalue_ma10 >= 0, red otherwise.
    """
    df = df.sort_values("positive_net_ratio_10d", ascending=True).copy()

    bar_colors = df["cumsumnetvalue_ma10"].apply(
        lambda v: PHASE_COLORS["Accumulation"] if v >= 0 else PHASE_COLORS["Distribution"]
    )

    fig = go.Figure(
        go.Bar(
            y=df["stockcode"],
            x=df["positive_net_ratio_10d"],
            orientation="h",
            marker_color=bar_colors,
            text=df["positive_net_ratio_10d"].apply(lambda v: f"{v:.0%}"),
            textposition="outside",
            customdata=np.stack([
                df["price_return_pct"],
                df["foreign_percentage"],
                df["cumsumnetvalue_ma10"],
            ], axis=1),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Pos-day ratio: %{x:.0%}<br>"
                "10d return: %{customdata[0]:+.2f}%<br>"
                "Foreign ownership: %{customdata[1]:.1f}%<br>"
                "Cum. net flow: %{customdata[2]:,.0f}<br>"
                "<extra></extra>"
            ),
        )
    )

    fig.update_xaxes(title="Positive Net Flow Ratio (10d)", range=[0, 1.2])
    fig.update_layout(
        title=f"{sector} — Stocks Ranked by Flow Momentum",
        height=max(380, len(df) * 26 + 80),
        margin=dict(l=80, r=80, t=55, b=40),
        paper_bgcolor=BG,
        plot_bgcolor=PLOT_BG,
        yaxis=dict(tickfont=dict(size=10)),
    )
    return fig


def fig_stock_ownership(df: pd.DataFrame, sector: str) -> go.Figure:
    """
    Scatter: X = foreign_percentage, Y = price_return_pct
    Size & label = stockcode, color = positive_net_ratio_10d
    Useful to see if high-foreign-ownership stocks are moving.
    """
    fig = px.scatter(
        df,
        x="foreign_percentage",
        y="price_return_pct",
        size="bubble_size",
        color="positive_net_ratio_10d",
        color_continuous_scale="Blues",
        range_color=[0, 1],
        text="stockcode",
        hover_name="stockcode",
        hover_data={
            "sector":                 False,
            "foreign_percentage":     ":.1f",
            "price_return_pct":       ":.2f",
            "cumsumnetvalue_ma10":    ":,.0f",
            "positive_net_ratio_10d": ":.2f",
            "stockcode":              False,
            "bubble_size":            False,
        },
        size_max=35,
        title=f"{sector} — Foreign Ownership % vs Price Return  |  color = pos-day ratio",
    )

    fig.update_traces(
        textposition="top center",
        textfont=dict(size=8, color="#1E293B"),
        marker=dict(opacity=0.85, line=dict(width=0.5, color="white")),
    )

    fig.add_hline(y=0.0, line_dash="dot", line_color="#CBD5E1", line_width=1.5)
    fig.update_xaxes(title="Foreign Ownership (%)")
    fig.update_yaxes(title="Price Return 10d (%)")
    fig.update_coloraxes(colorbar_title="Pos-day ratio")
    fig.update_layout(
        height=500,
        margin=dict(l=40, r=40, t=60, b=40),
        paper_bgcolor=BG,
        plot_bgcolor=PLOT_BG,
    )
    return fig


# ─────────────────────────────────────────────────────────
# Inline CSS
# ─────────────────────────────────────────────────────────

STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.ff-title {
    font-size: 1.9rem; font-weight: 700; color: #0D9488;
    letter-spacing: -0.5px; margin-bottom: 0.15rem;
}
.ff-sub {
    font-size: 0.88rem; color: #64748B; margin-bottom: 1.4rem;
}
.kpi-row { display: flex; gap: 1rem; margin-bottom: 1.2rem; flex-wrap: wrap; }
.kpi-card {
    background: #fff; border-radius: 10px; padding: 0.9rem 1.2rem;
    border: 1px solid #E2E8F0; min-width: 130px; flex: 1;
}
.kpi-label  { font-size: 0.73rem; color: #94A3B8; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
.kpi-value  { font-size: 1.7rem; font-weight: 700; color: #0F172A; line-height: 1.2; }
.kpi-delta  { font-size: 0.78rem; font-weight: 500; margin-top: 2px; }
.delta-green { color: #10B981; }
.delta-red   { color: #EF4444; }
.delta-gray  { color: #94A3B8; }

.sector-info {
    display: flex; gap: 2rem; padding: 0.6rem 0; flex-wrap: wrap;
}
.sector-info .si-item { display: flex; flex-direction: column; }
.sector-info .si-label { font-size: 0.73rem; color: #94A3B8; font-weight: 500; }
.sector-info .si-value { font-size: 1.1rem; font-weight: 600; color: #0F172A; }
</style>
"""


# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────

def main() -> None:
    st.markdown(STYLES, unsafe_allow_html=True)

    # ── Title ──
    st.markdown(
        '<div class="ff-title">💹 Foreign Flow Explorer</div>'
        '<div class="ff-sub">Sector overview → drill down to individual stock level</div>',
        unsafe_allow_html=True,
    )

    # ── Load data ──
    with st.spinner("Loading…"):
        sector_df = load_sector()
        stock_df  = load_stocks()

    # ── KPI cards ──
    acc   = int((sector_df["flow_phase"] == "Accumulation").sum())
    dist  = int((sector_df["flow_phase"] == "Distribution").sum())
    neut  = int((sector_df["flow_phase"] == "Neutral").sum())
    total = len(sector_df)
    data_date = sector_df["date"].iloc[0] if "date" in sector_df.columns else "—"

    st.markdown(
        f"""
        <div class="kpi-row">
            <div class="kpi-card">
                <div class="kpi-label">Data as of</div>
                <div class="kpi-value" style="font-size:1.1rem;">{data_date}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Total Sectors</div>
                <div class="kpi-value">{total}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Accumulation</div>
                <div class="kpi-value">{acc}</div>
                <div class="kpi-delta delta-green">▲ {acc/total:.0%} of sectors</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Distribution</div>
                <div class="kpi-value">{dist}</div>
                <div class="kpi-delta delta-red">▼ {dist/total:.0%} of sectors</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Neutral</div>
                <div class="kpi-value">{neut}</div>
                <div class="kpi-delta delta-gray">{neut/total:.0%} of sectors</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Stocks Tracked</div>
                <div class="kpi-value">{len(stock_df):,}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # ══════════════════════════════════════════
    # SECTION 1 — Sector Overview
    # ══════════════════════════════════════════
    st.subheader("1 · Sector Overview")
    st.caption(
        "Treemap sizes sectors by absolute net flow magnitude. "
        "Quadrant scatter shows flow momentum (X) vs price return (Y)."
    )

    tab_tree, tab_quad = st.tabs(["🗺 Treemap", "⊕ Quadrant Scatter"])

    with tab_tree:
        st.plotly_chart(fig_treemap(sector_df), use_container_width=True)

    with tab_quad:
        st.plotly_chart(fig_sector_quadrant(sector_df), use_container_width=True)

    st.divider()

    # ══════════════════════════════════════════
    # SECTION 2 — Stock Deep Dive
    # ══════════════════════════════════════════
    st.subheader("2 · Stock Deep Dive")
    st.caption("Select a sector to explore individual stocks within it.")

    # Sector selector
    sectors_available = sorted(
        stock_df["sector"].dropna().astype(str).unique().tolist(),
        key=str.lower,
    )
    col_sel, col_meta = st.columns([1, 3])

    with col_sel:
        selected = st.selectbox("Select sector", options=sectors_available)

    sub = stock_df[stock_df["sector"].astype(str) == selected].copy()

    with col_meta:
        if not sub.empty:
            n_stocks      = len(sub)
            avg_ratio     = sub["positive_net_ratio_10d"].mean()
            avg_ret       = sub["price_return_pct"].mean()
            net_cum_total = sub["cumsumnetvalue_ma10"].sum()
            avg_foreign   = sub["foreign_percentage"].mean()

            net_color = "delta-green" if net_cum_total >= 0 else "delta-red"
            ret_color = "delta-green" if avg_ret >= 0 else "delta-red"

            st.markdown(
                f"""
                <div class="sector-info" style="padding-top:0.9rem;">
                    <div class="si-item">
                        <span class="si-label">Stocks</span>
                        <span class="si-value">{n_stocks}</span>
                    </div>
                    <div class="si-item">
                        <span class="si-label">Avg pos-day ratio</span>
                        <span class="si-value">{avg_ratio:.0%}</span>
                    </div>
                    <div class="si-item">
                        <span class="si-label">Avg 10d return</span>
                        <span class="si-value {ret_color}">{avg_ret:+.2f}%</span>
                    </div>
                    <div class="si-item">
                        <span class="si-label">Total cum. net flow</span>
                        <span class="si-value {net_color}">{net_cum_total:,.0f}</span>
                    </div>
                    <div class="si-item">
                        <span class="si-label">Avg foreign ownership</span>
                        <span class="si-value">{avg_foreign:.1f}%</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if sub.empty:
        st.info(f"No stock data found for sector: {selected}")
    else:
        tab_scatter, tab_bar, tab_ownership = st.tabs([
            "⊕ Flow Scatter",
            "▤ Flow Ranking",
            "◉ Ownership vs Return",
        ])

        with tab_scatter:
            st.caption(
                "X = positive net-flow ratio (how often foreigners were net buyers in past 10 days)  |  "
                "Y = 10-day price return (%)  |  "
                "Bubble size = foreign ownership %  |  "
                "Color = cumulative net flow (green = net inflow, red = net outflow)"
            )
            st.plotly_chart(fig_stock_scatter(sub, selected), use_container_width=True)

        with tab_bar:
            st.caption(
                "Stocks ranked by positive net-flow ratio. "
                "Green bars = positive cumulative net flow, red bars = negative."
            )
            st.plotly_chart(fig_stock_bar(sub, selected), use_container_width=True)

        with tab_ownership:
            st.caption(
                "X = foreign ownership %  |  Y = 10-day price return (%)  |  "
                "Color = positive-day ratio (darker blue = stronger consistent buying)"
            )
            st.plotly_chart(fig_stock_ownership(sub, selected), use_container_width=True)

    st.divider()

    # ── Raw data expander ──
    with st.expander("Raw data tables"):
        c1, c2 = st.columns(2)
        with c1:
            st.caption("Sector flow (all sectors)")
            disp_sector = sector_df.drop(columns=["sub_sector_label", "flow_size"], errors="ignore")
            st.dataframe(
                disp_sector.sort_values("positive_net_ratio_10d", ascending=False),
                height=320,
                use_container_width=True,
                hide_index=True,
            )
        with c2:
            st.caption(f"Stock flow — {selected}")
            disp_stock = sub.drop(columns=["bubble_size", "price_return_pct"], errors="ignore")
            st.dataframe(
                disp_stock.sort_values("positive_net_ratio_10d", ascending=False),
                height=320,
                use_container_width=True,
                hide_index=True,
            )


if __name__ == "__main__":
    main()
