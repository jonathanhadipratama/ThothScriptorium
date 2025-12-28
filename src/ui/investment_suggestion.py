# src/ui/investment_suggestion.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st


# ---------------------------------------------------------------------
# DATA LOADER
# ---------------------------------------------------------------------

def load_investment_suggestion_json(
    stock_code: str,
    *,
    output_dir: Path = Path("output/code_analysis"),
) -> Optional[Dict[str, Any]]:
    """
    Loads investment suggestion JSON for a given stock code.
    Returns None if file doesn't exist or JSON is invalid.
    """
    stock_code = str(stock_code).strip().upper()
    path = output_dir / f"{stock_code}_investment_analysis.json"

    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ---------------------------------------------------------------------
# RENDERER
# ---------------------------------------------------------------------

def render_investment_suggestion(s: Dict[str, Any]) -> None:
    """
    Renders the investment suggestion panel for a single stock.
    """
    if not isinstance(s, dict) or not s:
        st.warning("Investment suggestion not available.")
        return

    company = s.get("company", "-")
    sector = s.get("sector", "-")
    stance = s.get("investment_stance", "-")
    synthesis = s.get("investment_synthesis", "")
    profile = s.get("investment_profile", "-")

    strengths = s.get("key_strengths", []) or []
    risks = s.get("key_risks", []) or []
    ddl = s.get("further_due_diligence", []) or []

    # ------------------- Header -------------------
    st.subheader("Investment Suggestion")

    c1, c2, c3 = st.columns([1.1, 1.1, 1.8])
    with c1:
        st.caption("Company")
        st.markdown(f"**{company}**")
    with c2:
        st.caption("Sector")
        st.markdown(f"**{sector}**")
    with c3:
        st.caption("Investment stance")
        st.markdown(f"**{stance}**")

    st.caption("Investment synthesis")
    st.write(synthesis or "-")

    st.caption("Investment profile")
    st.markdown(f"**{profile}**")

    st.markdown("---")

    # ------------------- Strengths vs Risks -------------------
    left, right = st.columns(2)

    with left:
        st.subheader("Key strengths")
        if strengths:
            for item in strengths:
                st.markdown(f"- {item}")
        else:
            st.write("-")

    with right:
        st.subheader("Key risks")
        if risks:
            for item in risks:
                st.markdown(f"- {item}")
        else:
            st.write("-")

    st.markdown("---")

    # ------------------- Further Due Diligence -------------------
    st.subheader("Further due diligence")
    if ddl:
        for item in ddl:
            st.markdown(f"- {item}")
    else:
        st.write("-")


# ---------------------------------------------------------------------
# STANDALONE TEST MODE
# ---------------------------------------------------------------------

if __name__ == "__main__":
    st.set_page_config(
        page_title="Investment Suggestion – Test",
        layout="wide",
    )

    st.title("Investment Suggestion Component – Standalone Test")

    # You can change this while testing
    DEFAULT_CODE = "ULTJ"

    stock_code = st.text_input("Stock code", value=DEFAULT_CODE)
    output_dir = Path("output/code_analysis")

    suggestion = load_investment_suggestion_json(stock_code, output_dir=output_dir)

    if suggestion is None:
        st.warning(
            f"No investment suggestion JSON found for `{stock_code}` "
            f"in `{output_dir.as_posix()}`"
        )
    else:
        render_investment_suggestion(suggestion)
