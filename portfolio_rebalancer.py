"""
Portfolio Rebalancer — Streamlit page
IDX equal-weight 3-stock portfolio with periodic rebalancing.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import streamlit as st

from src.ui.theme import load_theme_css
from src.backtest_engine import BacktestEngine
from src.data_processor import DataProcessor
from src.ui.portfolio_charts import (
    plot_equity,
    plot_weights,
    plot_cumulative_return,
    plot_drawdown,
    plot_rebal_bars,
    plot_rolling_corr,
    plot_price_paths,
)

# ── Theme ─────────────────────────────────────────────────────
load_theme_css()

BASE_DIR    = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "data" / "portfolio" / "dataset.csv"

INITIAL_CAPITAL = 10_000_000.0

FREQ_LABELS = {
    "weekly":    "Weekly",
    "biweekly":  "Bi-weekly",
    "monthly":   "Monthly",
    "quarterly": "Quarterly",
}

STOCK_COLOURS = {
    0: {"bg": "#eef2ff", "text": "#4f46e5"},   # blue
    1: {"bg": "#ecfdf5", "text": "#059669"},   # green
    2: {"bg": "#fffbeb", "text": "#d97706"},   # amber
}


# ── Cached data loader ────────────────────────────────────────
@st.cache_resource(show_spinner="Loading IDX dataset…")
def get_processor() -> DataProcessor:
    dp = DataProcessor(str(DATASET_PATH))
    dp.load()
    return dp


# ── Session state defaults ────────────────────────────────────
for key, default in [
    ("rebal_result", None),
    ("rebal_stocks", [None, None, None]),
    ("rebal_period", "monthly"),
    ("top_pct", 20),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── Helper: format Rupiah ────────────────────────────────────
def fmt_rp(v: float) -> str:
    if abs(v) >= 1_000_000_000:
        return f"Rp {v/1_000_000_000:.2f}B"
    if abs(v) >= 1_000_000:
        return f"Rp {v/1_000_000:.2f}M"
    return f"Rp {v:,.0f}"


# ── Helper: render KPI grid ───────────────────────────────────
def _kpi_grid(stats: dict, stocks: list) -> str:
    def kpi(label: str, value: str, sub: str = "", cls: str = "") -> str:
        return (
            f'<div class="kpi-card">'
            f'  <div class="kpi-label">{label}</div>'
            f'  <div class="kpi-value {cls}">{value}</div>'
            f'  {"<div class=kpi-sub>" + sub + "</div>" if sub else ""}'
            f'</div>'
        )

    tr   = stats["total_return"]
    ar   = stats["annual_return"]
    bh   = stats["bh_return"]
    ex   = stats["excess_return"]
    sh   = stats["sharpe"]
    md   = stats["max_drawdown"]
    rc   = stats["rebal_count"]
    fees = stats["total_fees"]
    fv   = stats["final_value"]

    tr_cls  = "pos" if tr  >= 0 else "neg"
    ar_cls  = "pos" if ar  >= 0 else "neg"
    ex_cls  = "pos" if ex  >= 0 else "neg"
    sh_cls  = "pos" if sh  >= 0 else "neg"

    cards = [
        kpi("Total Return",    f"{tr:+.2f}%",   f"Initial {fmt_rp(INITIAL_CAPITAL)}",  tr_cls),
        kpi("Annual Return",   f"{ar:+.2f}%",   "Annualised",                          ar_cls),
        kpi("vs Equal B&H",    f"{ex:+.2f}%",   f"B&H: {bh:+.2f}%",                   ex_cls),
        kpi("Sharpe Ratio",    f"{sh:.2f}",      "Daily rf=0, ×√252",                  sh_cls),
        kpi("Max Drawdown",    f"-{md:.2f}%",    "Peak-to-trough",                      "neg"),
        kpi("Rebalancings",    str(rc),           "Events executed"),
        kpi("Fees Paid",       fmt_rp(fees),      "Buy + sell fees"),
        kpi("Final Value",     fmt_rp(fv),         "End of period"),
    ]
    return f'<div class="kpi-grid">{"".join(cards)}</div>'


# ── Helper: render beat/miss banner ──────────────────────────
def _banner(stats: dict) -> str:
    ex = stats["excess_return"]
    cls = "beat" if ex >= 0 else "miss"
    verdict = "Beat equal-weight B&H" if ex >= 0 else "Underperformed equal-weight B&H"
    return (
        f'<div class="banner {cls}">'
        f'  <div>'
        f'    <div class="banner-text">{verdict}</div>'
        f'    <div class="banner-sub">'
        f'      Strategy {stats["total_return"]:+.2f}% vs B&H {stats["bh_return"]:+.2f}%'
        f'    </div>'
        f'  </div>'
        f'  <div class="banner-value">{ex:+.2f}%</div>'
        f'</div>'
    )


# ── Helper: correlation heatmap HTML ─────────────────────────
def _corr_heatmap(matrix: dict, stocks: list) -> str:
    def cell_bg(v: float) -> str:
        if v == 1.0:
            return "#f9fafb"
        intensity = int(abs(v) * 80)
        if v > 0:
            return f"rgba(220,38,38,{abs(v):.2f})"
        return f"rgba(5,150,105,{abs(v):.2f})"

    rows = ""
    header = "<tr><th></th>" + "".join(f"<th>{s}</th>" for s in stocks) + "</tr>"
    for a in stocks:
        row = f"<tr><th>{a}</th>"
        for b in stocks:
            v = matrix[a][b]
            bg = cell_bg(v)
            txt = "1.00" if v == 1.0 else f"{v:+.3f}"
            row += f'<td style="background:{bg};color:{"#111827" if v == 1.0 else "#fff"}">{txt}</td>'
        row += "</tr>"
        rows += row
    return (
        '<div style="overflow-x:auto">'
        f'<table class="heatmap-table">{header}{rows}</table>'
        '</div>'
    )


# ── Helper: rebalancing event log HTML ───────────────────────
def _rebal_table(events: list, stocks: list) -> str:
    if not events:
        return '<p style="color:#9ca3af;font-size:13px;padding:12px 0">No rebalancing events executed.</p>'

    header_cols = ["Date", "Port. Value"] + [f"{s} Action" for s in stocks] + ["Cash After"]
    thead = "<tr>" + "".join(f"<th>{c}</th>" for c in header_cols) + "</tr>"

    rows = ""
    for ev in events:
        pv   = fmt_rp(ev["portfolio_value"])
        cash = fmt_rp(ev["cash_after"])
        row  = f"<tr><td>{ev['date']}</td><td>{pv}</td>"
        for s in stocks:
            t = ev["trades"].get(s)
            if t:
                action = t["action"]
                cls    = "tag-buy" if action == "BUY" else "tag-sell"
                detail = f'{t["shares"]:,} sh @ Rp{t["price"]:,.0f}'
                row   += f'<td><span class="tag {cls}">{action}</span>&nbsp;{detail}</td>'
            else:
                row += '<td style="color:#9ca3af">–</td>'
        row += f"<td>{cash}</td></tr>"
        rows += row

    return (
        '<div class="rebal-table-wrap">'
        f'<table><thead>{thead}</thead><tbody>{rows}</tbody></table>'
        '</div>'
    )


# ═══════════════════════════════════════════════════════════════
#   PAGE RENDER
# ═══════════════════════════════════════════════════════════════

processor = get_processor()
meta      = processor.get_top20_stocks()

# ── Page header ───────────────────────────────────────────────
st.markdown(
    '<p class="section-title">IDX · Portfolio Rebalancer</p>'
    '<div class="info-row">'
    f'  <span class="info-pill">Period <strong>{meta["date_range"]["start"][:7]} – {meta["date_range"]["end"][:7]}</strong></span>'
    f'  <span class="info-pill">Trading Days <strong>{meta["total_dates"]:,}</strong></span>'
    f'  <span class="info-pill">Eligible Stocks <strong>{len(processor.all_ranked_stocks):,}</strong></span>'
    f'  <span class="info-pill">Initial Capital <strong>Rp 10,000,000</strong></span>'
    '</div>',
    unsafe_allow_html=True,
)

# ── Configure section ─────────────────────────────────────────
st.markdown('<p class="section-title" style="margin-top:8px">Configure</p>', unsafe_allow_html=True)

# Top-% slider
top_pct = st.slider(
    "Universe: top % of stocks by 2025 volume",
    min_value=5, max_value=100, step=5,
    value=st.session_state.top_pct,
    key="top_pct_slider",
)
st.session_state.top_pct = top_pct

stock_universe = processor.get_stocks_by_pct(top_pct)
code_to_name   = {s["code"]: f'{s["code"]} – {s["name"]}' for s in stock_universe}
codes          = [s["code"] for s in stock_universe]

# 3-column stock pickers
col1, col2, col3 = st.columns(3)
col_configs = [
    (col1, "Stock 1 (Blue)", 0),
    (col2, "Stock 2 (Green)", 1),
    (col3, "Stock 3 (Amber)", 2),
]

selected_stocks: List[Optional[str]] = [None, None, None]
for col, label, idx in col_configs:
    prev = st.session_state.rebal_stocks[idx]
    default_idx = codes.index(prev) if prev and prev in codes else 0
    with col:
        chosen = st.selectbox(
            label,
            options=codes,
            index=default_idx,
            format_func=lambda c: code_to_name.get(c, c),
            key=f"stock_picker_{idx}",
        )
        selected_stocks[idx] = chosen

st.session_state.rebal_stocks = selected_stocks

# Auto-select button
auto_col, _ = st.columns([2, 6])
with auto_col:
    if st.button("⚡ Auto-Select Uncorrelated Trio", use_container_width=True):
        with st.spinner("Finding uncorrelated trio…"):
            trio_result = processor.find_uncorrelated_trio(n_candidates=60, top_pct=top_pct)
            if "error" not in trio_result:
                st.session_state.rebal_stocks = trio_result["stocks"]
                st.rerun()
            else:
                st.error(trio_result["error"])

# Show correlation mini-matrix if all 3 stocks differ
stocks_chosen = st.session_state.rebal_stocks
if (
    all(s is not None for s in stocks_chosen)
    and len(set(stocks_chosen)) == 3
):
    with st.spinner("Computing correlation…"):
        corr_data = processor.compute_correlation(stocks_chosen)
    matrix = corr_data["matrix"]

    # Mini correlation badges
    pairs = [
        (stocks_chosen[0], stocks_chosen[1]),
        (stocks_chosen[0], stocks_chosen[2]),
        (stocks_chosen[1], stocks_chosen[2]),
    ]
    badge_html = '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px;">'
    for a, b in pairs:
        v   = matrix[a][b]
        cls = "pos" if v <= 0.3 else ("neg" if v >= 0.6 else "")
        badge_html += (
            f'<span class="info-pill">'
            f'{a}↔{b}: <strong class="{cls}">{v:+.3f}</strong>'
            f'</span>'
        )
    badge_html += '</div>'
    st.markdown(badge_html, unsafe_allow_html=True)

st.divider()

# ── Backtest settings ─────────────────────────────────────────
st.markdown('<p class="section-title">Backtest Settings</p>', unsafe_allow_html=True)

freq_col, run_col = st.columns([4, 1])
with freq_col:
    freq = st.radio(
        "Rebalancing frequency",
        options=list(FREQ_LABELS.keys()),
        format_func=lambda k: FREQ_LABELS[k],
        index=list(FREQ_LABELS.keys()).index(st.session_state.rebal_period),
        horizontal=True,
        key="freq_radio",
    )
    st.session_state.rebal_period = freq

with run_col:
    st.write("")  # spacing
    run_clicked = st.button("▶ Run Backtest", type="primary", use_container_width=True)

# ── Execute backtest ──────────────────────────────────────────
if run_clicked:
    stocks_for_bt = st.session_state.rebal_stocks
    if len(set(stocks_for_bt)) < 3:
        st.warning("Please select 3 distinct stocks before running.")
    else:
        with st.spinner("Running backtest…"):
            engine = BacktestEngine(processor)
            result = engine.run(stocks_for_bt, st.session_state.rebal_period)
            st.session_state.rebal_result = result

# ═══════════════════════════════════════════════════════════════
#   RESULTS
# ═══════════════════════════════════════════════════════════════
result = st.session_state.rebal_result

if result:
    stocks  = result["stocks"]
    stats   = result["stats"]

    st.divider()

    # Beat/miss banner
    st.markdown(_banner(stats), unsafe_allow_html=True)

    # KPI grid
    st.markdown(_kpi_grid(stats, stocks), unsafe_allow_html=True)

    # Tabs
    tab_overview, tab_rebal, tab_corr = st.tabs(["Overview", "Rebalancing", "Correlation"])

    # ── Overview ─────────────────────────────────────────────
    with tab_overview:
        st.markdown('<p class="section-title">Performance Overview</p>', unsafe_allow_html=True)
        st.plotly_chart(plot_equity(result),            use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(plot_weights(result),           use_container_width=True)
        with c2:
            st.plotly_chart(plot_cumulative_return(result), use_container_width=True)

        st.plotly_chart(plot_drawdown(result),          use_container_width=True)

    # ── Rebalancing ───────────────────────────────────────────
    with tab_rebal:
        st.markdown('<p class="section-title">Rebalancing Activity</p>', unsafe_allow_html=True)
        st.plotly_chart(plot_rebal_bars(result), use_container_width=True)

        st.markdown('<p class="section-title" style="margin-top:8px">Event Log</p>', unsafe_allow_html=True)
        st.markdown(
            _rebal_table(result["rebal_events"], stocks),
            unsafe_allow_html=True,
        )

    # ── Correlation ───────────────────────────────────────────
    with tab_corr:
        st.markdown('<p class="section-title">Correlation Analysis</p>', unsafe_allow_html=True)

        h1, h2 = st.columns(2)
        with h1:
            st.markdown("**Pairwise Correlation Matrix**")
            st.markdown(
                _corr_heatmap(result["correlation"]["matrix"], stocks),
                unsafe_allow_html=True,
            )
        with h2:
            st.plotly_chart(plot_rolling_corr(result), use_container_width=True)

        st.plotly_chart(plot_price_paths(result), use_container_width=True)
