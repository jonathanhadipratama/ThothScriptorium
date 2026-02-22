"""
Portfolio Rebalancer — Plotly chart helpers.
Mirrors the visual style of the claude_test Chart.js charts
using the same colour palette and clean card aesthetic.
"""
from __future__ import annotations

from typing import Any, Dict, List

import plotly.graph_objects as go

# ── Colour palette (matches claude_test CSS vars) ───────────
C_STRATEGY = "#111827"
C_BH       = "#9ca3af"
C_S1       = "#4f46e5"
C_S2       = "#059669"
C_S3       = "#d97706"
STOCK_COLOURS = [C_S1, C_S2, C_S3]

# rgba fill variants (0.55 alpha)
C_S1_FILL = "rgba(79,70,229,0.55)"
C_S2_FILL = "rgba(5,150,105,0.55)"
C_S3_FILL = "rgba(217,119,6,0.55)"
STOCK_FILLS = [C_S1_FILL, C_S2_FILL, C_S3_FILL]

# ── Shared layout defaults ───────────────────────────────────
def _base_layout(**kwargs) -> dict:
    base = dict(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter, system-ui, sans-serif", size=12, color="#111827"),
        margin=dict(l=0, r=0, t=32, b=0),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=11),
        ),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            tickfont=dict(size=10, color="#9ca3af"),
            linecolor="#e5e7eb",
        ),
    )
    base.update(kwargs)
    return base


def _fmt_rp(v: float) -> str:
    if abs(v) >= 1_000_000_000:
        return f"Rp {v/1_000_000_000:.2f}B"
    if abs(v) >= 1_000_000:
        return f"Rp {v/1_000_000:.2f}M"
    return f"Rp {v:,.0f}"


# ── 1. Equity curve ──────────────────────────────────────────
def plot_equity(result: Dict[str, Any]) -> go.Figure:
    dates    = result["dates"]
    stocks   = result["stocks"]
    eq       = [e["value"] for e in result["equity_curve"]]
    eq_bh    = [v["value"] for v in result["benchmarks"]["equal_bh"]]

    fig = go.Figure()

    # Strategy (bold)
    fig.add_trace(go.Scatter(
        x=dates, y=eq,
        name="Strategy",
        line=dict(color=C_STRATEGY, width=2),
        hovertemplate="%{x}<br>Strategy: %{customdata}<extra></extra>",
        customdata=[_fmt_rp(v) for v in eq],
    ))
    # Equal B&H
    fig.add_trace(go.Scatter(
        x=dates, y=eq_bh,
        name="Equal B&H",
        line=dict(color=C_BH, width=1.5, dash="dot"),
        hovertemplate="%{x}<br>Equal B&H: %{customdata}<extra></extra>",
        customdata=[_fmt_rp(v) for v in eq_bh],
    ))
    # Per-stock B&H
    for s, colour in zip(stocks, STOCK_COLOURS):
        bh = [v["value"] for v in result["benchmarks"].get(f"bh_{s}", [])]
        if bh:
            fig.add_trace(go.Scatter(
                x=dates, y=bh,
                name=f"{s} B&H",
                line=dict(color=colour, width=1, dash="dash"),
                hovertemplate=f"%{{x}}<br>{s} B&H: %{{customdata}}<extra></extra>",
                customdata=[_fmt_rp(v) for v in bh],
            ))

    fig.update_layout(
        **_base_layout(title=dict(text="Equity Curve", font=dict(size=14, weight=600))),
        height=320,
        yaxis=dict(tickprefix="Rp ", tickformat=",.0f", showgrid=True, gridcolor="#f3f4f6",
                   zeroline=False, tickfont=dict(size=10, color="#9ca3af")),
    )
    return fig


# ── 2. Portfolio weight drift (stacked area) ─────────────────
def plot_weights(result: Dict[str, Any]) -> go.Figure:
    dates  = result["dates"]
    stocks = result["stocks"]
    alloc  = result["allocation_hist"]

    fig = go.Figure()
    for s, colour, fill in zip(stocks, STOCK_COLOURS, STOCK_FILLS):
        weights = [a["weights"].get(s, 0) for a in alloc]
        fig.add_trace(go.Scatter(
            x=dates, y=weights,
            name=s,
            stackgroup="one",
            line=dict(color=colour, width=0),
            fillcolor=fill,
            hovertemplate=f"{s}: %{{y:.1f}}%<extra></extra>",
        ))

    fig.update_layout(
        **_base_layout(title=dict(text="Portfolio Weight Drift", font=dict(size=14, weight=600))),
        height=230,
        yaxis=dict(ticksuffix="%", range=[0, 100], showgrid=True, gridcolor="#f3f4f6",
                   zeroline=False, tickfont=dict(size=10, color="#9ca3af")),
    )
    return fig


# ── 3. Cumulative return comparison ──────────────────────────
def plot_cumulative_return(result: Dict[str, Any]) -> go.Figure:
    init   = 10_000_000.0
    dates  = result["dates"]
    stocks = result["stocks"]
    eq     = [e["value"] for e in result["equity_curve"]]
    eq_bh  = [v["value"] for v in result["benchmarks"]["equal_bh"]]

    def pct(vals):
        return [(v - init) / init * 100 for v in vals]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=pct(eq), name="Strategy",
                             line=dict(color=C_STRATEGY, width=2),
                             hovertemplate="%{x}<br>Strategy: %{y:.2f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=dates, y=pct(eq_bh), name="Equal B&H",
                             line=dict(color=C_BH, width=1.5, dash="dot"),
                             hovertemplate="%{x}<br>Equal B&H: %{y:.2f}%<extra></extra>"))
    for s, colour in zip(stocks, STOCK_COLOURS):
        bh = [v["value"] for v in result["benchmarks"].get(f"bh_{s}", [])]
        if bh:
            fig.add_trace(go.Scatter(x=dates, y=pct(bh), name=f"{s} B&H",
                                     line=dict(color=colour, width=1, dash="dash"),
                                     hovertemplate=f"{s}: %{{y:.2f}}%<extra></extra>"))

    fig.update_layout(
        **_base_layout(title=dict(text="Cumulative Return vs Benchmarks", font=dict(size=14, weight=600))),
        height=230,
        yaxis=dict(ticksuffix="%", showgrid=True, gridcolor="#f3f4f6",
                   zeroline=True, zerolinecolor="#e5e7eb",
                   tickfont=dict(size=10, color="#9ca3af")),
    )
    return fig


# ── 4. Drawdown ───────────────────────────────────────────────
def plot_drawdown(result: Dict[str, Any]) -> go.Figure:
    dates  = result["dates"]
    dd     = result["stats"]["drawdown_curve"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=dd,
        name="Drawdown",
        fill="tozeroy",
        line=dict(color="#dc2626", width=1),
        fillcolor="rgba(220,38,38,0.12)",
        hovertemplate="%{x}<br>Drawdown: %{y:.2f}%<extra></extra>",
    ))
    fig.update_layout(
        **_base_layout(title=dict(text="Drawdown", font=dict(size=14, weight=600))),
        height=160,
        yaxis=dict(ticksuffix="%", showgrid=True, gridcolor="#f3f4f6",
                   zeroline=True, zerolinecolor="#e5e7eb",
                   tickfont=dict(size=10, color="#9ca3af")),
    )
    return fig


# ── 5. Rebalancing bars ───────────────────────────────────────
def plot_rebal_bars(result: Dict[str, Any]) -> go.Figure:
    events = result["rebal_events"]
    stocks = result["stocks"]

    if not events:
        fig = go.Figure()
        fig.update_layout(**_base_layout(), height=230)
        return fig

    event_dates = [e["date"] for e in events]

    fig = go.Figure()
    for s, colour in zip(stocks, STOCK_COLOURS):
        vals = []
        for ev in events:
            t = ev["trades"].get(s)
            vals.append(t["value"] if t else 0)
        fig.add_trace(go.Bar(
            x=event_dates, y=vals,
            name=s,
            marker_color=colour,
            hovertemplate=f"{s}: Rp%{{y:,.0f}}<extra></extra>",
        ))

    fig.update_layout(
        **_base_layout(
            title=dict(text="Trade Amounts per Rebalancing Event", font=dict(size=14, weight=600)),
            barmode="group",
        ),
        height=230,
        yaxis=dict(tickprefix="Rp ", tickformat=",.0f", showgrid=True, gridcolor="#f3f4f6",
                   zeroline=False, tickfont=dict(size=10, color="#9ca3af")),
    )
    return fig


# ── 6. Rolling 20-day correlation ────────────────────────────
def plot_rolling_corr(result: Dict[str, Any]) -> go.Figure:
    dates   = result["dates"]
    rolling = result["correlation"]["rolling"]

    colours = [C_S1, C_S2, C_S3]
    fig = go.Figure()
    for (pair, vals), colour in zip(rolling.items(), colours):
        # Replace None with NaN placeholder for Plotly
        y = [v if v is not None else float("nan") for v in vals]
        fig.add_trace(go.Scatter(
            x=dates, y=y,
            name=pair,
            line=dict(color=colour, width=1.5),
            hovertemplate=f"{pair}: %{{y:.3f}}<extra></extra>",
            connectgaps=False,
        ))

    fig.add_hline(y=0, line_dash="dot", line_color="#e5e7eb")
    fig.update_layout(
        **_base_layout(title=dict(text="Rolling 20-Day Correlation", font=dict(size=14, weight=600))),
        height=230,
        yaxis=dict(range=[-1, 1], showgrid=True, gridcolor="#f3f4f6",
                   zeroline=False, tickfont=dict(size=10, color="#9ca3af")),
    )
    return fig


# ── 7. Normalised price paths ────────────────────────────────
def plot_price_paths(result: Dict[str, Any]) -> go.Figure:
    dates  = result["dates"]
    stocks = result["stocks"]
    alloc  = result["allocation_hist"]

    # Reconstruct weight per stock to get a proxy for price path via benchmarks
    # We'll use the per-stock B&H values, normalised to 100
    fig = go.Figure()
    for s, colour in zip(stocks, STOCK_COLOURS):
        bh_series = result["benchmarks"].get(f"bh_{s}", [])
        if not bh_series:
            continue
        bh_vals = [v["value"] for v in bh_series]
        base = bh_vals[0] if bh_vals[0] else 1
        normalised = [v / base * 100 for v in bh_vals]
        fig.add_trace(go.Scatter(
            x=dates, y=normalised,
            name=s,
            line=dict(color=colour, width=1.8),
            hovertemplate=f"{s}: %{{y:.1f}}<extra></extra>",
        ))

    fig.add_hline(y=100, line_dash="dot", line_color="#e5e7eb")
    fig.update_layout(
        **_base_layout(title=dict(text="Normalised Price Paths (Base = 100)", font=dict(size=14, weight=600))),
        height=280,
        yaxis=dict(showgrid=True, gridcolor="#f3f4f6", zeroline=False,
                   tickfont=dict(size=10, color="#9ca3af")),
    )
    return fig
