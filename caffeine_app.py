import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- Helper functions ---
def caffeine_remaining(dose_mg, elapsed_hr, half_life):
    return dose_mg * (0.5 ** (elapsed_hr / half_life))

def cumulative_caffeine(doses, hours, half_life):
    total = np.zeros_like(hours, dtype=float)
    for day, dose_time, dose_mg in doses:
        total_hr = dose_time + day*24
        elapsed = hours - total_hr
        elapsed[elapsed < 0] = 0
        total += caffeine_remaining(dose_mg, elapsed, half_life)
    return total

def hours_to_day_hour_min(hours):
    day = int(hours // 24) + 1
    hour = int(hours % 24)
    minute = int((hours*60) % 60)
    return day, hour, minute

def format_hours_label(hours):
    day, hour, minute = hours_to_day_hour_min(hours)
    return f"Day {day} {hour:02d}:{minute:02d}"

def plot_cumulative_caffeine(doses, selected_total_hr):
    if not doses:
        return None

    first_dose_total = min(day*24 + t for day, t, _ in doses)
    last_dose_total = max(day*24 + t for day, t, _ in doses)
    points = min(500, int(last_dose_total - first_dose_total + 24))
    hours = np.linspace(first_dose_total, last_dose_total + 24, points)

    half_lives = {"Min (3h)":3, "Average (5h)":5, "Max (7h)":7}

    caffeine_min_curve = cumulative_caffeine(doses, hours, half_lives["Min (3h)"])
    caffeine_avg_curve = cumulative_caffeine(doses, hours, half_lives["Average (5h)"])
    caffeine_max_curve = cumulative_caffeine(doses, hours, half_lives["Max (7h)"])

    fig = go.Figure()

    # Min-Max shaded area
    fig.add_traces([
        go.Scatter(x=hours, y=caffeine_max_curve, line=dict(width=0), showlegend=False),
        go.Scatter(x=hours, y=caffeine_min_curve, fill='tonexty', fillcolor='rgba(173,216,230,0.3)',
                   line=dict(width=0), name='Min–Max Range')
    ])

    # Average line
    fig.add_trace(go.Scatter(
        x=hours, y=caffeine_avg_curve, mode='lines', name='Average (5h)',
        line=dict(color='blue', width=2)
    ))

    # Points at selected time
    for label, hl, color in [("Min (3h)", 3, "red"), ("Average (5h)", 5, "blue"), ("Max (7h)", 7, "green")]:
        val = cumulative_caffeine(doses, np.array([selected_total_hr]), hl)[0]
        fig.add_trace(go.Scatter(
            x=[selected_total_hr], y=[val],
            mode='markers+text',
            marker=dict(color=color, size=10),
            text=[f"{val:.0f} mg"],
            textposition="top center",
            name=label
        ))

    # Vertical lines for doses
    for day, dose_time, dose_mg in doses:
        total_hr = dose_time + day*24
        fig.add_vline(x=total_hr, line=dict(color='gray', dash='dash'))

    # Dynamic x-axis ticks
    tick_interval = max(1, round((last_dose_total - first_dose_total + 24) / 10))
    tick_vals = np.arange(np.floor(first_dose_total), np.ceil(last_dose_total + 24)+1, tick_interval)
    tick_texts = [format_hours_label(v) for v in tick_vals]

    fig.update_layout(
        title="Cumulative Caffeine",
        xaxis=dict(title="Time", tickvals=tick_vals, ticktext=tick_texts),
        yaxis_title="Caffeine Remaining (mg)",
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5, font=dict(size=10)),
        margin=dict(l=30, r=20, t=40, b=100),
        dragmode=False
    )

    return fig

# --- Session state ---
defaults = {
    "doses": [],
    "dose_value": 100,
    "day": 1,
    "hour": 8,
    "minute": 0,
    "selected_total_hr": 0
}
for key, default in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- Callbacks ---
def change_value(key, delta, min_val=0):
    st.session_state[key] = max(min_val, st.session_state[key] + delta)

def change_minute(delta):
    total_min = st.session_state.minute + delta
    extra_hour = total_min // 60
    st.session_state.minute = total_min % 60
    change_hour(extra_hour)

def change_hour(delta):
    total_hour = st.session_state.hour + delta
    extra_day = total_hour // 24
    st.session_state.hour = total_hour % 24
    change_value("day", extra_day, 1)

def add_dose_value(delta):
    change_value("dose_value", delta, 0)

# --- App UI ---
st.title("☕ Caffeine Tracker")

# --- Caffeine Dose Input ---
st.subheader("Caffeine Dose (mg)")
with st.container():
    plus_cols = st.columns([1,1,1])
    for i, val in enumerate([100,10,1]):
        plus_cols[i].button(f"+{val}", on_click=lambda v=val: add_dose_value(v), key=f"dose_plus_{val}")
    st.number_input("", key="dose_value", min_value=0, step=1, label_visibility="collapsed")
    minus_cols = st.columns([1,1,1])
    for i, val in enumerate([100,10,1]):
        minus_cols[i].button(f"-{val}", on_click=lambda v=-val: add_dose_value(v), key=f"dose_minus_{val}")

st.markdown("---")

# --- Day / Hour / Minute Input ---
st.subheader("Day / Time of Dose")
for key, label, max_val, callback in zip(["day","hour","minute"], ["Day","Hour","Minute"], [None,23,59], [change_value, change_hour, change_minute]):
    with st.container():
        plus_cols = st.columns([1,1])
        plus_cols[0].button("+10", on_click=lambda f=callback: f(10), key=f"{key}_plus_10")
        plus_cols[1].button("+1", on_click=lambda f=callback: f(1), key=f"{key}_plus_1")
        st.number_input(label, key=key, min_value=0, max_value=max_val, step=1)
        minus_cols = st.columns([1,1])
        minus_cols[0].button("-10", on_click=lambda f=callback: f(-10), key=f"{key}_minus_10")
        minus_cols[1].button("-1", on_click=lambda f=callback: f(-1), key=f"{key}_minus_1")
    st.markdown("---")

# --- Add / Clear Doses ---
if st.button("Add Dose"):
    st.session_state.doses.append(
        (st.session_state.day-1, st.session_state.hour + st.session_state.minute/60, st.session_state.dose_value)
    )
if st.button("Clear All Doses"):
    st.session_state.doses = []
    st.session_state.selected_total_hr = 0

# --- Time Slider / Nudge ---
if st.session_state.doses:
    first_dose_total = min(day*24 + t for day, t, _ in st.session_state.doses)
    last_dose_total = max(day*24 + t for day, t, _ in st.session_state.doses)
    max_total_hr = last_dose_total + 24

    if st.session_state.selected_total_hr < first_dose_total:
        st.session_state.selected_total_hr = first_dose_total

    st.subheader("Select Time")
    nudg_cols = st.columns([2,2,2,6,2,2,2])
    if nudg_cols[0].button("-10h"): st.session_state.selected_total_hr = max(first_dose_total, st.session_state.selected_total_hr-10)
    if nudg_cols[1].button("-1h"): st.session_state.selected_total_hr = max(first_dose_total, st.session_state.selected_total_hr-1)
    if nudg_cols[2].button("-15m"): st.session_state.selected_total_hr = max(first_dose_total, st.session_state.selected_total_hr-0.25)

    st.session_state.selected_total_hr = nudg_cols[3].slider(
        "Time",
        float(first_dose_total),
        float(max_total_hr),
        float(st.session_state.selected_total_hr),
        step=0.25,
        label_visibility="collapsed"
    )

    if nudg_cols[4].button("+15m"): st.session_state.selected_total_hr = min(max_total_hr, st.session_state.selected_total_hr+0.25)
    if nudg_cols[5].button("+1h"): st.session_state.selected_total_hr = min(max_total_hr, st.session_state.selected_total_hr+1)
    if nudg_cols[6].button("+10h"): st.session_state.selected_total_hr = min(max_total_hr, st.session_state.selected_total_hr+10)

    # --- Chart ---
    fig = plot_cumulative_caffeine(st.session_state.doses, st.session_state.selected_total_hr)
    st.plotly_chart(fig, use_container_width=True)

    # --- Caffeine Info ---
    st.subheader("Caffeine at Selected Time")
    half_lives = {"Min (3h)":3, "Average (5h)":5, "Max (7h)":7}
    for label, hl in half_lives.items():
        remaining = cumulative_caffeine(st.session_state.doses, np.array([st.session_state.selected_total_hr]), hl)[0]
        st.write(f"{label}: **{remaining:.0f} mg**")

    # --- Dose Table ---
    with st.expander("View All Doses"):
        for idx, (day, dose_time, dose_mg) in enumerate(st.session_state.doses):
            hour = int(dose_time)
            minute = int(round((dose_time - hour) * 60))
            cols = st.columns([1,1,1,1,1])
            cols[0].write(idx+1)
            cols[1].write(dose_mg)
            cols[2].write(day+1)
            cols[3].write(f"{hour:02d}:{minute:02d}")
            if cols[4].button("Delete", key=f"delete_{idx}"):
                st.session_state.doses.pop(idx)
                st.rerun()
else:
    st.info("Add one or more doses to see the chart and table.")
