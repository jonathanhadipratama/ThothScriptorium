import pandas as pd
import numpy as np
import streamlit as st
import altair as alt

from data_extraction import get_bigquery_client, get_all_and_quarterly, PROJECT_ID


# ---------- Helpers for scaling numbers ---------- #

def get_scale_and_unit(max_abs_value: float):
    """
    Given the maximum absolute value of a series, decide whether to scale by:
    - Million (M)
    - Billion (B)
    - Trillion (T)
    or leave as is.

    Returns:
        scale (float), unit (str)
    """
    if max_abs_value >= 1_000_000_000_000:
        return 1_000_000_000_000, "T"
    elif max_abs_value >= 1_000_000_000:
        return 1_000_000_000, "B"
    elif max_abs_value >= 1_000_000:
        return 1_000_000, "M"
    else:
        return 1.0, ""


# ---------- Data extraction ---------- #

code = "CMRY"

client = get_bigquery_client(PROJECT_ID)
df_all, df_quarter = get_all_and_quarterly(code, client)

# ---------- Prep data ---------- #

quarter_order = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}

df = df_quarter[df_quarter["year"].isin([2023, 2024, 2025])].copy()
df["quarter_num"] = df["quarter"].map(quarter_order)
df["period"] = df["year"].astype(str) + " " + df["quarter"]

df = df.sort_values(["year", "quarter_num"])

st.title(f"{code} Quarterly Fundamentals")

params = sorted(df["parameter"].unique())

# ---------- UI: parameter selectors in one row ---------- #

col1, col2 = st.columns(2)

with col1:
    left_param = st.selectbox(
        "LEFT axis parameter",
        params,
        index=0,
    )

with col2:
    right_param = st.selectbox(
        "RIGHT axis parameter",
        params,
        index=1 if len(params) > 1 else 0,
    )

# ---------- Button to trigger chart ---------- #

run = st.button("Generate chart")

if not run:
    st.info("Choose parameters, then click **Generate chart** to see the plot.")
else:
    base = alt.Chart(df).encode(
        x=alt.X(
            "period:N",
            sort=list(df["period"].unique()),
            title="Period",
        )
    )

    # ---------- Single-axis case (same parameter on both sides) ---------- #
    if left_param == right_param:
        series_df = df[df["parameter"] == left_param]

        if series_df.empty:
            st.warning(f"No data available for parameter: {left_param}")
        else:
            max_abs = series_df["value_final"].abs().max()
            scale, unit = get_scale_and_unit(max_abs)

            axis_title = left_param if unit == "" else f"{left_param} ({unit})"

            chart = (
                base.transform_filter(
                    alt.datum.parameter == left_param
                )
                .transform_calculate(
                    scaled_value=f"datum.value_final / {scale}"
                )
                .mark_line(point=True)
                .encode(
                    y=alt.Y(
                        "scaled_value:Q",
                        axis=alt.Axis(title=axis_title),
                    ),
                    color=alt.value("#1f77b4"),
                    tooltip=[
                        alt.Tooltip("parameter:N", title="Parameter"),
                        alt.Tooltip("period:N", title="Period"),
                        alt.Tooltip("year:Q", title="Year"),
                        alt.Tooltip("quarter:N", title="Quarter"),
                        alt.Tooltip(
                            "scaled_value:Q",
                            title=axis_title,
                            format=".2f",
                        ),
                    ],
                )
            )

            st.write(f"Showing **{left_param}** over time (scaled to {unit or 'original units'}).")
            st.altair_chart(chart, use_container_width=True)

    # ---------- Dual-axis case (different parameters) ---------- #
    else:
        left_df = df[df["parameter"] == left_param]
        right_df = df[df["parameter"] == right_param]

        if left_df.empty:
            st.warning(f"No data available for LEFT parameter: {left_param}")
        if right_df.empty:
            st.warning(f"No data available for RIGHT parameter: {right_param}")

        if left_df.empty or right_df.empty:
            st.stop()

        # Decide scaling for each axis
        max_left = left_df["value_final"].abs().max()
        max_right = right_df["value_final"].abs().max()

        scale_left, unit_left = get_scale_and_unit(max_left)
        scale_right, unit_right = get_scale_and_unit(max_right)

        axis_title_left = left_param if unit_left == "" else f"{left_param} ({unit_left})"
        axis_title_right = right_param if unit_right == "" else f"{right_param} ({unit_right})"

        left_line = (
            base.transform_filter(
                alt.datum.parameter == left_param
            )
            .transform_calculate(
                scaled_value=f"datum.value_final / {scale_left}"
            )
            .mark_line(point=True)
            .encode(
                y=alt.Y(
                    "scaled_value:Q",
                    axis=alt.Axis(title=axis_title_left),
                ),
                color=alt.value("#1f77b4"),
                tooltip=[
                    alt.Tooltip("parameter:N", title="Parameter"),
                    alt.Tooltip("period:N", title="Period"),
                    alt.Tooltip("year:Q", title="Year"),
                    alt.Tooltip("quarter:N", title="Quarter"),
                    alt.Tooltip(
                        "scaled_value:Q",
                        title=axis_title_left,
                        format=".2f",
                    ),
                ],
            )
        )

        right_line = (
            base.transform_filter(
                alt.datum.parameter == right_param
            )
            .transform_calculate(
                scaled_value=f"datum.value_final / {scale_right}"
            )
            .mark_line(point=True)
            .encode(
                y=alt.Y(
                    "scaled_value:Q",
                    axis=alt.Axis(title=axis_title_right, orient="right"),
                ),
                color=alt.value("#ff7f0e"),
                tooltip=[
                    alt.Tooltip("parameter:N", title="Parameter"),
                    alt.Tooltip("period:N", title="Period"),
                    alt.Tooltip("year:Q", title="Year"),
                    alt.Tooltip("quarter:N", title="Quarter"),
                    alt.Tooltip(
                        "scaled_value:Q",
                        title=axis_title_right,
                        format=".2f",
                    ),
                ],
            )
        )

        chart = alt.layer(left_line, right_line).resolve_scale(
            y="independent"  # separate y-scales for left/right axes
        )

        st.write(
            f"Showing **{left_param}** (left axis, scaled to {unit_left or 'original units'}) "
            f"and **{right_param}** (right axis, scaled to {unit_right or 'original units'})."
        )
        st.altair_chart(chart, use_container_width=True)
