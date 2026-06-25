"""
Streamlit dashboard for SAPMS.

Visualizes the attendance and productivity data that attendance_tracker.py
writes into MySQL.

Run with:
    streamlit run dashboard.py
"""

from datetime import date, datetime

import pandas as pd
import streamlit as st

import database

st.set_page_config(page_title="SAPMS Dashboard", layout="wide")
st.title("Smart Attendance & Productivity Dashboard")

selected_date = st.sidebar.date_input("Select date", value=date.today())

# ---------------- Attendance table ----------------
st.subheader(f"Attendance — {selected_date}")

attendance_rows = database.get_attendance_for_date(selected_date)

if attendance_rows:
    df = pd.DataFrame(attendance_rows)

    def fmt_duration(row):
        # pd.isna() correctly catches both plain None and pandas' NaT marker.
        # A plain truthy check (`if row["check_out_time"]`) breaks once the
        # column contains a mix of real timestamps and missing values,
        # because NaT evaluates as True, not False.
        end = datetime.now() if pd.isna(row["check_out_time"]) else row["check_out_time"]
        delta = end - row["check_in_time"]
        total_minutes = int(delta.total_seconds() // 60)
        return f"{total_minutes // 60}h {total_minutes % 60}m"

    df["duration"] = df.apply(fmt_duration, axis=1)
    df["status"] = df["check_out_time"].apply(lambda x: "Present now" if pd.isna(x) else "Checked out")

    st.dataframe(
        df[["name", "role", "check_in_time", "check_out_time", "duration", "status"]],
        use_container_width=True,
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Present", len(df))
    col2.metric("Currently In", int(df["check_out_time"].isna().sum()))
    col3.metric("Checked Out", int(df["check_out_time"].notna().sum()))
else:
    st.info("No attendance records for this date yet.")

st.divider()

# ---------------- Productivity section ----------------
st.subheader(f"Productivity — {selected_date}")

prod_rows = database.get_productivity_for_date(selected_date)

if prod_rows:
    prod_df = pd.DataFrame(prod_rows)
    prod_df["active_seconds"] = prod_df["active_seconds"].fillna(0)
    prod_df["idle_seconds"] = prod_df["idle_seconds"].fillna(0)
    prod_df["total_seconds"] = prod_df["active_seconds"] + prod_df["idle_seconds"]
    prod_df["productivity_pct"] = (
        (prod_df["active_seconds"] / prod_df["total_seconds"].replace(0, 1)) * 100
    ).round(1)

    chart_col, table_col = st.columns([2, 1])

    with chart_col:
        st.bar_chart(prod_df.set_index("name")["productivity_pct"])

    with table_col:
        st.dataframe(
            prod_df[["name", "productivity_pct"]].rename(columns={"productivity_pct": "Productivity %"}),
            use_container_width=True,
        )

    st.metric("Average Productivity", f"{prod_df['productivity_pct'].mean():.1f}%")

    st.subheader("Per-person activity timeline")
    all_persons = database.get_all_persons()
    name_to_id = {p["name"]: p["person_id"] for p in all_persons}

    if name_to_id:
        chosen_name = st.selectbox("Choose a person", list(name_to_id.keys()))
        timeline_rows = database.get_activity_timeline(name_to_id[chosen_name], selected_date)

        if timeline_rows:
            tl_df = pd.DataFrame(timeline_rows)
            tl_df["log_time"] = pd.to_datetime(tl_df["log_time"])
            st.line_chart(tl_df.set_index("log_time")["duration_seconds"])
        else:
            st.info("No activity logs for this person on this date yet.")
else:
    st.info("No productivity data for this date yet.")

st.divider()

# ---------------- Weekly trend ----------------
st.subheader("Weekly Attendance Trend (last 7 days)")
weekly_rows = database.get_weekly_attendance_count()

if weekly_rows:
    weekly_df = pd.DataFrame(weekly_rows)
    weekly_df["session_date"] = weekly_df["session_date"].astype(str)
    st.bar_chart(weekly_df.set_index("session_date")["present_count"])
else:
    st.info("Not enough data yet to show a weekly trend.")