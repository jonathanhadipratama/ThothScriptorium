import streamlit as st
import altair as alt


def get_scale_and_unit(max_abs_value: float):
    """
    Decide whether to scale by Million (M), Billion (B), Trillion (T), or not at all.
    Returns (scale, unit).
    """
    if max_abs_value >= 1_000_000_000_000:
        return 1_000_000_000_000, "T"
    elif max_abs_value >= 1_000_000_000:
        return 1_000_000_000, "B"
    elif max_abs_value >= 1_000_000:
        return 1_000_000, "M"
    else:
        return 1.0, ""


def quarterly_fundamental_chart(code: str, df_quarter):
    """
    Render a dual-axis quarterly fundamentals chart for the given stock code,
    using the provided df_quarter dataframe.
    """
    st.subheader("Quarterly Fundamentals Chart")

    if df_quarter is None or df_quarter.empty:
        st.warning(f"No quarterly data found for {code}.")
        return

    # ---------- Prep data ---------- #
    quarter_order = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}

    df = df_quarter.copy()
    df["quarter_num"] = df["quarter"].map(quarter_order)
    df["period"] = df["year"].astype(str) + " " + df["quarter"]
    df = df.sort_values(["year", "quarter_num"])

    params = sorted(df["parameter"].unique())
    if not params:
        st.warning("No parameters available to plot.")
        return

    # ---------- UI: parameter selectors in one row ---------- #
    col1, col2 = st.columns(2)

    with col1:
        left_param = st.selectbox(
            "LEFT axis parameter",
            params,
            index=0,
            key=f"{code}_left_param",
        )

    with col2:
        right_param = st.selectbox(
            "RIGHT axis parameter",
            params,
            index=1 if len(params) > 1 else 0,
            key=f"{code}_right_param",
        )

    # ---------- Button to trigger chart ---------- #
    run = st.button("Generate chart", key=f"{code}_generate_chart")

    if not run:
        st.info("Choose parameters, then click **Generate chart** to see the plot.")
        return

    base = alt.Chart(df).encode(
        x=alt.X(
            "period:N",
            sort=list(df["period"].unique()),
            title="Period",
        )
    )

    # ---------- Single-axis case (same parameter both sides) ---------- #
    if left_param == right_param:
        series_df = df[df["parameter"] == left_param]

        if series_df.empty:
            st.warning(f"No data available for parameter: {left_param}")
            return

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
                    alt.Tooltip("scaled_value:Q", title=axis_title, format=".2f"),
                ],
            )
        )

        st.write(
            f"Showing **{left_param}** over time "
            f"(scaled to {unit or 'original units'})."
        )
        st.altair_chart(chart, use_container_width=True)
        return

    # ---------- Dual-axis case (different parameters) ---------- #
    left_df = df[df["parameter"] == left_param]
    right_df = df[df["parameter"] == right_param]

    if left_df.empty:
        st.warning(f"No data available for LEFT parameter: {left_param}")
        return
    if right_df.empty:
        st.warning(f"No data available for RIGHT parameter: {right_param}")
        return

    max_left = left_df["value_final"].abs().max()
    max_right = right_df["value_final"].abs().max()

    scale_left, unit_left = get_scale_and_unit(max_left)
    scale_right, unit_right = get_scale_and_unit(max_right)

    axis_title_left = left_param if unit_left == "" else f"{left_param} ({unit_left})"
    axis_title_right = (
        right_param if unit_right == "" else f"{right_param} ({unit_right})"
    )

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
                alt.Tooltip("scaled_value:Q", title=axis_title_left, format=".2f"),
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
                alt.Tooltip("scaled_value:Q", title=axis_title_right, format=".2f"),
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
