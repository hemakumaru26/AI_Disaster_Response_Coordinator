import json
import os
import pandas as pd
import streamlit as st

from app.components.cards import apply_custom_styles, render_admin_banner
from backend.database.connection import get_connection

apply_custom_styles()

render_admin_banner(
    title="Communications & Notification Dispatch Monitor",
    subtitle="Audit multi-channel alert delivery, Resend email dispatch logs, OSRM route ETAs, and coordinator notifications.",
)

# Notification Mode Detection
raw_mode = os.getenv("NOTIFICATION_MODE", "DRY_RUN").strip().upper()
notification_mode = "LIVE" if raw_mode == "LIVE" else "DRY_RUN"

col_mode1, col_mode2 = st.columns([3, 1])
with col_mode1:
    if notification_mode == "LIVE":
        st.success("🟢 **Active Dispatch Mode: LIVE** — Authorized messages are transmitted externally via Resend API.")
    else:
        st.info("🧪 **Active Dispatch Mode: DRY_RUN** — Notifications are safely simulated without sending live emails or incurring charges.")
with col_mode2:
    if st.button("🔄 Refresh Logs", use_container_width=True):
        st.rerun()


def load_all_communications():
    """Extract communications and dispatch logs across all missions in SQLite."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT m.mission_id, m.incident_id, m.status, m.approval_status,
                   m.rescue_plan_data, m.updated_at,
                   i.disaster_type, i.location
            FROM missions m
            LEFT JOIN incidents i ON m.incident_id = i.id
            WHERE m.rescue_plan_data IS NOT NULL
            ORDER BY m.mission_id DESC
            """
        ).fetchall()

    records = []
    for r in rows:
        try:
            plan = json.loads(r["rescue_plan_data"]) if r["rescue_plan_data"] else {}
            n_dispatch = plan.get("notification_dispatch") or {}
            results = n_dispatch.get("results") or []

            if results:
                for res in results:
                    records.append({
                        "mission_id": r["mission_id"],
                        "incident_id": r["incident_id"],
                        "disaster_type": r["disaster_type"] or "Emergency",
                        "location": r["location"] or "Tamil Nadu",
                        "channel": res.get("channel", "email"),
                        "recipient": res.get("recipient", "N/A"),
                        "subject": res.get("subject", "Emergency Notification"),
                        "status": res.get("status", "unknown").upper(),
                        "details": res.get("id") or res.get("reason") or res.get("error") or "Simulated dispatch",
                        "timestamp": r["updated_at"],
                    })
            else:
                comms = plan.get("communications") or {}
                messages = comms.get("messages") or []
                for msg in messages:
                    records.append({
                        "mission_id": r["mission_id"],
                        "incident_id": r["incident_id"],
                        "disaster_type": r["disaster_type"] or "Emergency",
                        "location": r["location"] or "Tamil Nadu",
                        "channel": msg.get("channel", "internal"),
                        "recipient": msg.get("recipient", "N/A"),
                        "subject": msg.get("subject", "Notification Prepared"),
                        "status": "PREPARED",
                        "details": f"Target: {msg.get('target', 'N/A')}",
                        "timestamp": r["updated_at"],
                    })
        except Exception:
            continue

    return pd.DataFrame(records)


df_comms = load_all_communications()

if df_comms.empty:
    st.info("No communication dispatch records found yet. Dispatches are generated upon mission approval.")
    st.stop()

# Metric summary
total_dispatches = len(df_comms)
submitted_count = len(df_comms[df_comms["status"] == "SUBMITTED"])
simulated_count = len(df_comms[df_comms["status"] == "SIMULATED"])
skipped_count = len(df_comms[df_comms["status"] == "SKIPPED"])
failed_count = len(df_comms[df_comms["status"] == "FAILED"])

m_c1, m_c2, m_c3, m_c4, m_c5 = st.columns(5)
m_c1.metric("Total Messages", f"{total_dispatches:,}")
m_c2.metric("Live Submitted", f"{submitted_count:,}")
m_c3.metric("Simulated", f"{simulated_count:,}")
m_c4.metric("Skipped", f"{skipped_count:,}")
m_c5.metric("Delivery Failures", f"{failed_count:,}")

st.markdown("---")

# Filter controls
f_col1, f_col2, f_col3 = st.columns([2, 2, 3])
all_statuses = ["All Statuses"] + sorted(df_comms["status"].unique().tolist())
selected_status = f_col1.selectbox("Filter by Status", all_statuses)

all_channels = ["All Channels"] + sorted(df_comms["channel"].unique().tolist())
selected_channel = f_col2.selectbox("Filter by Channel", all_channels)

search_text = f_col3.text_input("Search Recipient or Subject", "")

filtered_df = df_comms.copy()
if selected_status != "All Statuses":
    filtered_df = filtered_df[filtered_df["status"] == selected_status]

if selected_channel != "All Channels":
    filtered_df = filtered_df[filtered_df["channel"] == selected_channel]

if search_text.strip():
    q = search_text.strip().lower()
    filtered_df = filtered_df[
        filtered_df["recipient"].str.lower().str.contains(q, na=False)
        | filtered_df["subject"].str.lower().str.contains(q, na=False)
    ]

st.subheader(f"📋 Dispatch Log Entries ({len(filtered_df)} items)")
st.dataframe(
    filtered_df.rename(columns={
        "mission_id": "Mission ID",
        "incident_id": "Incident ID",
        "disaster_type": "Disaster",
        "location": "Location",
        "channel": "Channel",
        "recipient": "Recipient",
        "subject": "Subject",
        "status": "Status",
        "details": "Dispatch Notes",
        "timestamp": "Timestamp",
    }),
    use_container_width=True,
    hide_index=True,
)

