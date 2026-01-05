import streamlit as st
import datetime as dt
from pathlib import Path
import html

REFLECTION_FILE = Path("data/reflection.txt")


def load_reflection() -> str:
    if REFLECTION_FILE.exists():
        return REFLECTION_FILE.read_text(encoding="utf-8")
    return ""


def week_counter_2026_section():
    YEAR = 2026
    TOTAL_WEEKS = 53

    today = dt.date.today()
    if today.year < YEAR:
        passed_weeks = 0
    elif today.year > YEAR:
        passed_weeks = TOTAL_WEEKS
    else:
        passed_weeks = min(TOTAL_WEEKS, today.isocalendar().week)

    reflection_text = html.escape(load_reflection())

    st.markdown(
        """
<style>
.week-card{
  border:1px solid rgba(0,0,0,.15);
  border-radius:10px;
  padding:12px;
  max-width:320px;
  margin:0 auto;
  font-size:12px;
}
.week-title{
  font-size:15px;
  font-weight:600;
  margin-bottom:8px;
}
.week-grid{
  display:grid;
  grid-template-columns:repeat(10,12px);
  gap:5px;
  justify-content:center;
}
.week-box{
  width:12px;height:12px;
  border-radius:3px;
  border:1px solid rgba(0,0,0,.15);
}
.week-caption{
  margin-top:8px;
  color:#666;
  font-size:11px;
}
.reflection-title{
  margin-top:10px;
  font-weight:600;
  font-size:12px;
}
.reflection-box{
  margin-top:6px;
  width:100%;
  min-height:70px;
  resize:none;
  border-radius:8px;
  border:1px solid rgba(0,0,0,.12);
  padding:8px;
  font-size:12px;
  color:#444;
  background:#fafafa;
  box-sizing:border-box;
}
</style>
        """,
        unsafe_allow_html=True,
    )

    parts = []
    parts.append('<div class="week-card">')
    parts.append('<div class="week-title">2026 Week Counter</div>')
    parts.append('<div class="week-grid">')

    for week in range(1, TOTAL_WEEKS + 1):
        color = "#e53935" if week <= passed_weeks else "#43a047"
        parts.append(f'<div class="week-box" title="Week {week}" style="background:{color};"></div>')

    parts.append("</div>")  # week-grid
    parts.append(f'<div class="week-caption">Passed weeks: {passed_weeks}/{TOTAL_WEEKS}</div>')
    parts.append('<div class="reflection-title">Reflection for today</div>')
    parts.append(f'<textarea class="reflection-box" readonly>{reflection_text}</textarea>')
    parts.append("</div>")  # week-card

    st.markdown("".join(parts), unsafe_allow_html=True)


if __name__ == "__main__":
    st.set_page_config(page_title="Week Counter 2026", layout="centered")
    week_counter_2026_section()
