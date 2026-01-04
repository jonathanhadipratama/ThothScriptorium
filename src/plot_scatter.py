"""
Streamlit app: RSI Weekly vs Monthly Scatterplot (text labels, no legend)

- X-axis: rsi_weekly
- Y-axis: rsi_monthly
- Axes fixed from 0 to 100
- sub_sector shown directly as text on each point
- Labels ONLY for points outside RSI neutral zone (30–70) on either axis
- Hover shows: flow_phase, vision_group, relevancy, source
- Reads data from data/rsi/rsi_data.csv
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, List
from src.data_extraction import get_sector_rsi

import pandas as pd
import plotly.express as px
import streamlit as st


# =========================
# Configuration
# =========================

@dataclass(frozen=True)
class AppConfig:
    data_path: Path = Path("data/rsi/rsi_data.csv")

    x_col: str = "rsi_weekly"
    y_col: str = "rsi_monthly"

    label_col: str = "sub_sector"
    hover_cols: Tuple[str, ...] = (
        "flow_phase",
        "vision_group",
        "relevancy",
        "source",
    )

    axis_min: int = 0
    axis_max: int = 100

    neutral_low: int = 35
    neutral_high: int = 65


# =========================
# Data Layer
# =========================

# def load_data(path: Path) -> pd.DataFrame:
#     if not path.exists():
#         raise FileNotFoundError(f"Data file not found: {path.resolve()}")
#     return pd.read_csv(path)


def prepare_data(df: pd.DataFrame, required_cols: List[str], x_col: str, y_col: str) -> Tuple[pd.DataFrame, int]:
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    clean = df.copy()

    # Coerce RSI columns
    clean[x_col] = pd.to_numeric(clean[x_col], errors="coerce")
    clean[y_col] = pd.to_numeric(clean[y_col], errors="coerce")

    before = len(clean)
    clean = clean.dropna(subset=[x_col, y_col])
    dropped = before - len(clean)

    # Ensure label & hover fields are strings
    for col in required_cols:
        if col not in [x_col, y_col]:
            clean[col] = clean[col].astype(str)

    return clean, dropped


def add_label_mask(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    label_col: str,
    neutral_low: float,
    neutral_high: float,
) -> pd.DataFrame:
    """
    Create a 'point_label' column that is only populated for points outside the neutral band.
    Condition:
      label if (x < low OR x > high OR y < low OR y > high)
    """
    out = df.copy()
    outside = (
        (out[x_col] < neutral_low)
        | (out[x_col] > neutral_high)
        | (out[y_col] < neutral_low)
        | (out[y_col] > neutral_high)
    )
    out["point_label"] = out[label_col].where(outside, "")
    return out


# =========================
# Plotting
# =========================

def create_scatterplot(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    label_col_for_plot: str,
    hover_cols: Tuple[str, ...],
    axis_min: int,
    axis_max: int,
    neutral_low: int,
    neutral_high: int,
):
    hover_data = {c: True for c in hover_cols if c in df.columns}

    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        text=label_col_for_plot,     # uses filtered labels
        hover_data=hover_data,
        title="RSI Weekly vs Monthly",
        opacity=0.85,
    )

    fig.update_traces(
        textposition="top center",
        marker=dict(size=8),
        showlegend=False,
    )

    fig.update_xaxes(range=[axis_min, axis_max], title=x_col)
    fig.update_yaxes(range=[axis_min, axis_max], title=y_col)

    # Neutral zone guide lines (optional but helpful)
    fig.add_vline(x=neutral_low, line_width=1)
    fig.add_vline(x=neutral_high, line_width=1)
    fig.add_hline(y=neutral_low, line_width=1)
    fig.add_hline(y=neutral_high, line_width=1)

    fig.update_layout(
        height=650,
        margin=dict(l=40, r=40, t=60, b=40),
    )

    return fig


# =========================
# Streamlit App
# =========================

def run_app(cfg: AppConfig) -> None:
    # st.set_page_config(page_title="RSI Scatterplot", layout="wide")
    st.title("Momentum Scatter")
    st.subheader("RSI Weekly vs Monthly")
    st.caption(
        f"Axes fixed from {cfg.axis_min}–{cfg.axis_max}. "
        f"Labels only for points outside RSI neutral zone ({cfg.neutral_low}–{cfg.neutral_high}) on either axis."
    )

    required_cols = [cfg.x_col, cfg.y_col, cfg.label_col, *cfg.hover_cols]

    try:
        df = get_sector_rsi()
        df_clean, dropped_rows = prepare_data(df, required_cols, cfg.x_col, cfg.y_col)
    except Exception as e:
        st.error(str(e))
        st.stop()

    if dropped_rows > 0:
        st.info(f"Dropped {dropped_rows} row(s) due to missing or non-numeric RSI values.")

    df_plot = add_label_mask(
        df_clean,
        x_col=cfg.x_col,
        y_col=cfg.y_col,
        label_col=cfg.label_col,
        neutral_low=cfg.neutral_low,
        neutral_high=cfg.neutral_high,
    )

    fig = create_scatterplot(
        df_plot,
        x_col=cfg.x_col,
        y_col=cfg.y_col,
        label_col_for_plot="point_label",
        hover_cols=cfg.hover_cols,
        axis_min=cfg.axis_min,
        axis_max=cfg.axis_max,
        neutral_low=cfg.neutral_low,
        neutral_high=cfg.neutral_high,
    )

    st.plotly_chart(fig, use_container_width=True)


def render_scatter() -> None:
    cfg = AppConfig()
    run_app(cfg)


if __name__ == "__main__":
    render_scatter()
