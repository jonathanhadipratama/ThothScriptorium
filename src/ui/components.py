from pathlib import Path
from typing import List, Dict, Any
import json

import pandas as pd
import streamlit as st

from src.plot_sankey import plot_income_sankey


def hero_section(codes: list[str]) -> str:
    """Render hero + ticker selector, return chosen code."""
    with st.container():
        st.markdown(
            """
            <div class="hero">
                <div class="hero-left">
                    <div class="hero-badge">
                        <span>📈 Income flows</span>
                        <span style="opacity:0.7;">9M financial view</span>
                    </div>
                    <div class="hero-title">
                        Explore profit flows like a destination map
                    </div>
                    <div class="hero-subtitle">
                        Compare listed companies’ income statements as intuitive Sankey 
                        diagrams – see how each rupiah of revenue travels through costs, 
                        taxes, and finally lands in net profit.
                    </div>
                </div>
                <div class="hero-right">
                    <div class="card" style="min-width: 260px;">
                        <div class="card-title">Choose stock</div>
                        <div class="pill-select-label">Select a ticker to visualize</div>
            """,
            unsafe_allow_html=True,
        )

        code = st.selectbox(
            "Stock code",
            codes,
            index=0,
            label_visibility="collapsed",
        )

        st.markdown(
            """
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return code


def load_payload(data_dir: Path, code: str) -> tuple[pd.DataFrame, List[str], Dict[str, Any]]:
    payload = json.loads((data_dir / f"{code}.json").read_text(encoding="utf-8"))
    table = pd.DataFrame(payload["table"])
    summary = payload.get("summary", [])
    meta = payload.get("meta", {})
    return table, summary, meta


def sankey_section(code: str) -> None:
    st.markdown(
        """
        <div class="section-header">Income statement flow</div>
        <div class="section-sub">
            Sankey view of revenue, COGS, operating expenses, tax and net profit.
        </div>
        """,
        unsafe_allow_html=True,
    )
    fig = plot_income_sankey(code)
    st.plotly_chart(fig, use_container_width=True)


def commentary_and_snapshot(summary: List[str], meta: Dict[str, Any]) -> None:
    left_col, right_col = st.columns([1.6, 1.1], gap="large")

    # ---------- LEFT: Snapshot card ----------
    with left_col:
        if meta:
            company  = meta.get("company", "")
            period   = meta.get("period_label", "")
            currency = meta.get("currency", "IDR")
            unit     = meta.get("unit", "million")

            snapshot_html = f"""
            <div class="card-light">
                <div class="card-title">Snapshot</div>
                <div style="font-size:0.85rem;color:#0f172a;margin-bottom:0.25rem;">
                    <b>{company}</b>
                </div>
                <div style="font-size:0.8rem;color:#64748b;margin-bottom:0.4rem;">
                    {period}
                </div>
                <div style="font-size:0.8rem;color:#6b7280;">
                    <div>Currency: <b>{currency}</b></div>
                    <div>Units: <b>{unit}</b></div>
                </div>
            </div>
            """
            st.markdown(snapshot_html, unsafe_allow_html=True)

    # ---------- RIGHT: Commentary card (all inside one box) ----------
    with right_col:
        # Build the list items
        if isinstance(summary, list) and summary:
            items_html = "".join(
                f"<li>{s}</li>"
                for s in summary
            )
        else:
            items_html = """
                <li style='color:#6b7280;'>No summary provided.</li>
            """

        # Render the commentary card
        st.markdown(
            f"""
            <div class="card-light">
                <div class="card-title">Quick story for this period</div>
                <ul class="comment-list">
                    {items_html}
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )





def raw_table_section(table: pd.DataFrame) -> None:
    st.markdown(
        """
        <div style="margin-top:1.8rem;" />
        <div class="section-header">Underlying table</div>
        <div class="section-sub">
            Standardized rows extracted from the financial statements, used to build the Sankey.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="dataframe-wrap">', unsafe_allow_html=True)
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)
