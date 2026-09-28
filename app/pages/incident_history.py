import pandas as pd
import requests
import streamlit as st

from app.components.cards import apply_custom_styles, render_admin_banner
from backend.database.connection import get_connection

apply_custom_styles()

render_admin_banner(
    title="Incident History",
    subtitle="Complete database records of all reported emergency incidents, AI triage severity, and status.",
)


def load_incident_history():
    """Load all incidents directly from SQLite with fallback to emergency history API."""
    try:
        with get_connection() as conn:
            df = pd.read_sql_query(
                "SELECT * FROM incidents ORDER BY id DESC",
                conn,
            )
            return df
    except Exception:
        pass

    try:
        resp = requests.get("http://localhost:8000/emergency/history", timeout=5)
        if resp.status_code == 200:
            return pd.DataFrame(resp.json())
    except Exception:
        pass

    return pd.DataFrame()


df_incidents = load_incident_history()

if df_incidents.empty:
    st.info("No incidents available in the database.")
    st.stop()

# Header Metrics
tot = len(df_incidents)
crit = len(df_incidents[df_incidents["priority"] == "CRITICAL"]) if "priority" in df_incidents.columns else 0
high = len(df_incidents[df_incidents["priority"] == "HIGH"]) if "priority" in df_incidents.columns else 0
med = len(df_incidents[df_incidents["priority"] == "MEDIUM"]) if "priority" in df_incidents.columns else 0
low = len(df_incidents[df_incidents["priority"] == "LOW"]) if "priority" in df_incidents.columns else 0

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Incidents", f"{tot:,}")
m2.metric("Critical", f"{crit:,}")
m3.metric("High Priority", f"{high:,}")
m4.metric("Medium Priority", f"{med:,}")
m5.metric("Low Priority", f"{low:,}")

st.markdown("---")

# Filter controls
f1, f2, f3, f4 = st.columns([2, 2, 3, 1])

p_options = ["All Priorities"]
if "priority" in df_incidents.columns:
    p_options += [p for p in ["CRITICAL", "HIGH", "MEDIUM", "LOW"] if p in df_incidents["priority"].unique()]
sel_priority = f1.selectbox("Filter Priority", p_options)

d_options = ["All Hazards"]
if "disaster_type" in df_incidents.columns:
    d_options += sorted([d for d in df_incidents["disaster_type"].dropna().unique() if str(d).strip()])
sel_disaster = f2.selectbox("Filter Disaster Type", d_options)

search_q = f3.text_input("Search Location, Reporter or Description", "")

with f4:
    st.write("")
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

filtered = df_incidents.copy()

if sel_priority != "All Priorities" and "priority" in filtered.columns:
    filtered = filtered[filtered["priority"] == sel_priority]

if sel_disaster != "All Hazards" and "disaster_type" in filtered.columns:
    filtered = filtered[filtered["disaster_type"] == sel_disaster]

if search_q.strip():
    q = search_q.strip().lower()
    mask = False
    for col in ["location", "reporter_name", "description", "phone", "resources"]:
        if col in filtered.columns:
            mask = mask | filtered[col].astype(str).str.lower().str.contains(q, na=False)
    if "id" in filtered.columns:
        mask = mask | filtered["id"].astype(str).str.contains(q, na=False)
    filtered = filtered[mask]

# Show the exact database dataframe with all columns like before
st.subheader(f"📋 Incident Records ({len(filtered)} items)")
st.dataframe(
    filtered,
    use_container_width=True,
    hide_index=False,
)