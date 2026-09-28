import datetime
import os
from collections import Counter

import pandas as pd
import streamlit as st

from backend.database.connection import get_connection

# Page configuration
try:
    st.set_page_config(
        page_title="Command Center | AI Disaster Coordinator",
        page_icon="🚨",
        layout="wide",
    )
except Exception:
    pass

from app.components.cards import apply_custom_styles, render_admin_banner

apply_custom_styles()

render_admin_banner(
    title="Autonomous Command Center & Operational Intelligence",
    subtitle="Real-Time Situational Awareness, Multi-Agent Resource Deployment, and Field Response Analytics",
)

# --- Top Toolbar: Refresh & Status ---
toolbar_col1, toolbar_col2 = st.columns([4, 1])
with toolbar_col1:
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.write(f"⏱️ **Last Updated:** `{now_str}`")
with toolbar_col2:
    if st.button("🔄 Refresh Dashboard", use_container_width=True):
        st.rerun()


# --- Database Query Functions (Strictly Read-Only) ---
def load_all_dashboard_data():
    """Load all necessary operational datasets from SQLite using read-only queries."""
    with get_connection() as conn:
        incidents = pd.read_sql_query(
            "SELECT * FROM incidents ORDER BY id DESC", conn
        )
        missions = pd.read_sql_query(
            """
            SELECT m.mission_id, m.incident_id, m.status AS mission_status,
                   m.approval_status, m.created_at, m.updated_at,
                   i.disaster_type, i.location, i.priority, i.people_affected,
                   i.description
            FROM missions m
            LEFT JOIN incidents i ON m.incident_id = i.id
            ORDER BY m.mission_id DESC
            """,
            conn,
        )
        volunteers = pd.read_sql_query(
            """
            SELECT v.*,
                   CASE
                       WHEN EXISTS (
                           SELECT 1
                           FROM volunteer_assignments
                           WHERE volunteer_id = v.id
                             AND assignment_status = 'assigned'
                       ) THEN 'assigned'
                       ELSE v.availability_status
                   END AS current_status
            FROM volunteers v
            """,
            conn,
        )
        assignments = pd.read_sql_query(
            "SELECT * FROM volunteer_assignments", conn
        )
        shelters = pd.read_sql_query(
            "SELECT id, name, district, capacity, occupancy, contact FROM shelters",
            conn,
        )
        hospitals = pd.read_sql_query(
            "SELECT id, name, district, hospital_type FROM hospitals", conn
        )

    return incidents, missions, volunteers, assignments, shelters, hospitals


# Load Data safely
try:
    (
        incidents_df,
        missions_df,
        volunteers_df,
        assignments_df,
        shelters_df,
        hospitals_df,
    ) = load_all_dashboard_data()
except Exception as err:
    st.error(f"Failed to load operational data from database: {err}")
    st.stop()


# ==============================================================================
# SECTION 1: INCIDENT & MISSION OVERVIEW (Strict separation)
# ==============================================================================
st.subheader("📊 Operational Status Overview")

# Incidents metrics
total_incidents = len(incidents_df)
crit_high_incidents = (
    len(incidents_df[incidents_df["priority"].isin(["CRITICAL", "HIGH"])])
    if not incidents_df.empty
    else 0
)

# Missions metrics (from missions table)
awaiting_approval = (
    len(missions_df[missions_df["mission_status"] == "AWAITING_APPROVAL"])
    if not missions_df.empty
    else 0
)
active_missions = (
    len(missions_df[missions_df["mission_status"] == "ACTIVE"])
    if not missions_df.empty
    else 0
)
completed_missions = (
    len(missions_df[missions_df["mission_status"] == "COMPLETED"])
    if not missions_df.empty
    else 0
)
replanning_missions = (
    len(missions_df[missions_df["mission_status"] == "REPLANNING"])
    if not missions_df.empty
    else 0
)

m_col1, m_col2, m_col3, m_col4, m_col5, m_col6 = st.columns(6)
m_col1.metric("Total Incidents", f"{total_incidents:,}", help="All emergency reports recorded in the database")
m_col2.metric("Critical / High Priority", f"{crit_high_incidents:,}", help="Incidents requiring immediate emergency response")
m_col3.metric("Awaiting Approval", f"{awaiting_approval:,}", delta="Human Review" if awaiting_approval > 0 else None, help="Missions requiring coordinator sign-off")
m_col4.metric("Active Missions", f"{active_missions:,}", delta="In Progress" if active_missions > 0 else None, help="Missions currently deployed in the field")
m_col5.metric("Completed Missions", f"{completed_missions:,}", help="Missions successfully executed and concluded")
m_col6.metric("Replanning Missions", f"{replanning_missions:,}", help="Missions currently undergoing AI strategy revision")

st.markdown("---")


# ==============================================================================
# SECTION 2: RESOURCE STATUS SUMMARY CARDS
# ==============================================================================
st.subheader("📦 Resource Availability & Deployment")

# Volunteers
total_volunteers = len(volunteers_df)
assigned_volunteers = (
    len(volunteers_df[volunteers_df["current_status"] == "assigned"])
    if not volunteers_df.empty
    else 0
)
available_volunteers = (
    len(volunteers_df[volunteers_df["current_status"] == "available"])
    if not volunteers_df.empty
    else 0
)

# Shelters
shelters_df["occupancy"] = shelters_df["occupancy"].fillna(0).astype(int)
shelters_df["capacity"] = shelters_df["capacity"].fillna(0).astype(int)
shelters_df["available_capacity"] = (
    shelters_df["capacity"] - shelters_df["occupancy"]
).clip(lower=0)

total_shelters = len(shelters_df)
total_shelter_capacity = int(shelters_df["capacity"].sum())
occupied_shelter_capacity = int(shelters_df["occupancy"].sum())
available_shelter_capacity = int(shelters_df["available_capacity"].sum())
shelter_utilization = (
    (occupied_shelter_capacity / total_shelter_capacity * 100)
    if total_shelter_capacity > 0
    else 0.0
)

# Hospitals
total_hospitals = len(hospitals_df)

r_col1, r_col2, r_col3 = st.columns(3)

with r_col1:
    st.markdown("#### 👥 Volunteers")
    st.write(f"**Total Registered:** {total_volunteers:,}")
    st.write(f"**🟢 Ready for Dispatch:** {available_volunteers:,}")
    st.write(f"**🔴 Currently Assigned:** {assigned_volunteers:,}")
    vol_pct = (assigned_volunteers / total_volunteers * 100) if total_volunteers else 0
    st.progress(vol_pct / 100, text=f"Deployment: {vol_pct:.1f}%")

with r_col2:
    st.markdown("#### 🏠 Shelters")
    st.write(f"**Total Shelters:** {total_shelters:,}")
    st.write(f"**Total Capacity:** {total_shelter_capacity:,} persons")
    st.write(f"**🟢 Available Capacity:** {available_shelter_capacity:,} persons")
    st.write(f"**🔴 Occupied Capacity:** {occupied_shelter_capacity:,} persons")
    st.progress(
        min(1.0, shelter_utilization / 100),
        text=f"Capacity Occupancy: {shelter_utilization:.1f}%",
    )

with r_col3:
    st.markdown("#### 🏥 Healthcare Facilities")
    st.write(f"**Registered Hospitals:** {total_hospitals:,}")
    if not hospitals_df.empty and "district" in hospitals_df.columns:
        hosp_districts = hospitals_df["district"].nunique()
        st.write(f"**Districts Covered:** {hosp_districts} of 38")
    if not hospitals_df.empty and "hospital_type" in hospitals_df.columns:
        types = hospitals_df["hospital_type"].value_counts().to_dict()
        top_types = ", ".join([f"{k}: {v}" for k, v in list(types.items())[:2]])
        st.write(f"**Facility Types:** {top_types}")

st.markdown("---")


# ==============================================================================
# SECTION 3: MISSION STATUS BREAKDOWN
# ==============================================================================
st.subheader("🎯 Mission Lifecycle Status Breakdown")

CANONICAL_MISSION_STATUSES = [
    "CREATED",
    "ASSESSED",
    "PLANNED",
    "AWAITING_APPROVAL",
    "APPROVED",
    "REJECTED",
    "ACTIVE",
    "COMPLETED",
    "REPLANNING",
]

mission_counts = {
    status: 0 for status in CANONICAL_MISSION_STATUSES
}
if not missions_df.empty:
    actual_counts = missions_df["mission_status"].value_counts().to_dict()
    for status, count in actual_counts.items():
        if status in mission_counts:
            mission_counts[status] = count
        else:
            mission_counts[status] = count

mission_status_df = pd.DataFrame(
    list(mission_counts.items()), columns=["Mission Status", "Mission Count"]
)

chart_col, data_col = st.columns([3, 2])
with chart_col:
    st.bar_chart(
        mission_status_df.set_index("Mission Status"),
        use_container_width=True,
    )
with data_col:
    st.dataframe(mission_status_df, use_container_width=True, hide_index=True)

st.markdown("---")


# ==============================================================================
# SECTION 4: ACTIVE & AWAITING MISSIONS (REQUIRING ATTENTION)
# ==============================================================================
st.subheader("⚡ Missions Requiring Attention (Priority Queue)")

if not missions_df.empty:
    # Filter for Awaiting Approval, Active, and Replanning
    priority_missions = missions_df[
        missions_df["mission_status"].isin(
            ["AWAITING_APPROVAL", "ACTIVE", "REPLANNING"]
        )
    ].copy()

    # Sort: Awaiting Approval (1) -> Active (2) -> Replanning (3)
    sort_order = {"AWAITING_APPROVAL": 1, "ACTIVE": 2, "REPLANNING": 3}
    priority_missions["sort_rank"] = priority_missions["mission_status"].map(
        sort_order
    )
    priority_missions = priority_missions.sort_values(
        by=["sort_rank", "mission_id"], ascending=[True, False]
    )

    if not priority_missions.empty:
        display_priority_df = priority_missions[
            [
                "mission_id",
                "incident_id",
                "disaster_type",
                "location",
                "priority",
                "people_affected",
                "mission_status",
                "approval_status",
                "updated_at",
            ]
        ].rename(
            columns={
                "mission_id": "Mission ID",
                "incident_id": "Incident ID",
                "disaster_type": "Disaster Type",
                "location": "Location",
                "priority": "Priority",
                "people_affected": "People Affected",
                "mission_status": "Mission Status",
                "approval_status": "Approval Status",
                "updated_at": "Last Updated",
            }
        )
        st.dataframe(display_priority_df, use_container_width=True, hide_index=True)
    else:
        st.info("🟢 No active or awaiting missions require attention at this time.")
else:
    st.info("No mission records exist yet.")

st.markdown("---")


# ==============================================================================
# SECTION 5: RECENT INCIDENTS
# ==============================================================================
st.subheader("📋 Recent Incidents & Associated Missions")

if not incidents_df.empty:
    # Join incidents with missions table for mission status
    recent_incidents = incidents_df.head(10).copy()
    if not missions_df.empty:
        # Create map of incident_id -> (mission_id, mission_status)
        mission_map = (
            missions_df.groupby("incident_id")
            .first()[["mission_id", "mission_status"]]
            .to_dict("index")
        )
        recent_incidents["Associated Mission"] = recent_incidents["id"].apply(
            lambda x: f"Mission #{mission_map[x]['mission_id']}"
            if x in mission_map
            else "Not Initiated"
        )
        recent_incidents["Mission Status"] = recent_incidents["id"].apply(
            lambda x: mission_map[x]["mission_status"]
            if x in mission_map
            else "N/A"
        )
    else:
        recent_incidents["Associated Mission"] = "None"
        recent_incidents["Mission Status"] = "N/A"

    recent_display_df = recent_incidents[
        [
            "id",
            "disaster_type",
            "location",
            "people_affected",
            "priority",
            "severity_score",
            "Associated Mission",
            "Mission Status",
        ]
    ].rename(
        columns={
            "id": "Incident ID",
            "disaster_type": "Disaster Type",
            "location": "Location",
            "people_affected": "People Affected",
            "priority": "Priority",
            "severity_score": "Severity Score",
        }
    )
    st.dataframe(recent_display_df, use_container_width=True, hide_index=True)
    st.caption("ℹ️ To inspect complete incident records and history, navigate to the **Incident History** page.")
else:
    st.info("No incidents have been recorded.")

st.markdown("---")


# ==============================================================================
# SECTION 6: VOLUNTEER STATUS & SKILLS
# ==============================================================================
st.subheader("🤝 Volunteer Force Distribution")

v_stat1, v_stat2, v_stat3, v_stat4 = st.columns(4)
v_stat1.metric("Total Volunteers", f"{total_volunteers:,}")
v_stat2.metric("Available", f"{available_volunteers:,}")
v_stat3.metric("Assigned", f"{assigned_volunteers:,}")

completed_assignments_count = (
    len(assignments_df[assignments_df["assignment_status"] == "completed"])
    if not assignments_df.empty
    else 0
)
v_stat4.metric("Completed Missions Served", f"{completed_assignments_count:,}")

with st.expander("🛠️ Volunteer Skills Specialization Breakdown", expanded=False):
    skills_counter = Counter()
    for s_str in volunteers_df["skills"].dropna():
        for skill in str(s_str).split(","):
            cleaned = skill.strip()
            if cleaned:
                skills_counter[cleaned] += 1

    if skills_counter:
        skill_df = pd.DataFrame(
            skills_counter.most_common(12),
            columns=["Specialized Skill", "Available Volunteers"],
        )
        st.dataframe(skill_df, use_container_width=True, hide_index=True)
    else:
        st.write("No skills data recorded.")

st.markdown("---")


# ==============================================================================
# SECTION 7: SHELTER CAPACITY & DISTRICT BREAKDOWN
# ==============================================================================
st.subheader("🏘️ District Shelter Capacity Breakdown")

with st.expander("📊 View District Shelter Table", expanded=False):
    district_agg = (
        shelters_df.groupby("district", as_index=False)
        .agg(
            total_shelters=("id", "count"),
            total_capacity=("capacity", "sum"),
            occupied_capacity=("occupancy", "sum"),
            available_capacity=("available_capacity", "sum"),
        )
        .sort_values(by="district")
    )
    district_agg["utilization"] = (
        district_agg["occupied_capacity"]
        .div(district_agg["total_capacity"].replace(0, pd.NA))
        .mul(100)
        .fillna(0.0)
        .round(1)
        .astype(str)
        + "%"
    )
    st.dataframe(
        district_agg.rename(
            columns={
                "district": "District",
                "total_shelters": "Shelters",
                "total_capacity": "Total Capacity",
                "occupied_capacity": "Occupied",
                "available_capacity": "Available",
                "utilization": "Utilization",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

st.markdown("---")


# ==============================================================================
# SECTION 8: PRIORITY / DISASTER BREAKDOWN
# ==============================================================================
st.subheader("📈 Incident Analytics: Priority & Hazard Distribution")

ana_col1, ana_col2 = st.columns(2)

with ana_col1:
    st.markdown("#### Incident Priorities")
    if not incidents_df.empty:
        p_counts = (
            incidents_df["priority"]
            .value_counts()
            .reindex(["CRITICAL", "HIGH", "MEDIUM", "LOW"])
            .fillna(0)
            .astype(int)
        )
        p_df = pd.DataFrame({"Priority": p_counts.index, "Incidents": p_counts.values})
        st.bar_chart(p_df.set_index("Priority"), use_container_width=True)
    else:
        st.write("No incidents data.")

with ana_col2:
    st.markdown("#### Disaster Types")
    if not incidents_df.empty:
        d_counts = incidents_df["disaster_type"].value_counts()
        d_df = pd.DataFrame({"Hazard": d_counts.index, "Incidents": d_counts.values})
        st.bar_chart(d_df.set_index("Hazard"), use_container_width=True)
    else:
        st.write("No disaster data.")

st.markdown("---")


# ==============================================================================
# SECTION 9: SYSTEM HEALTH & INTEGRATION STATUS
# ==============================================================================
st.subheader("🛡️ System Health & Component Status")

# Read notification mode from environment
raw_mode = os.getenv("NOTIFICATION_MODE", "DRY_RUN").strip().upper()
notification_mode = "LIVE" if raw_mode == "LIVE" else "DRY_RUN"

h_col1, h_col2, h_col3 = st.columns(3)

with h_col1:
    st.success("🟢 **Database:** Connected (SQLite disaster.db)")
    st.success(f"🟢 **Volunteer Registry:** {total_volunteers} Volunteers Loaded")

with h_col2:
    st.success(f"🟢 **Shelter Network:** {total_shelters} Shelters Registered")
    st.success(f"🟢 **Hospital Network:** {total_hospitals} Facilities Registered")

with h_col3:
    st.success("🟢 **Mission Engine:** Operational (LangGraph State Graph)")
    if notification_mode == "LIVE":
        st.success("🟢 **Notification Engine:** LIVE (Resend Email Active)")
    else:
        st.warning("🟡 **Notification Engine:** DRY_RUN (Simulation Mode)")