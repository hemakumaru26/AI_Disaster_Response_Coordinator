import json
import re
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

from app.components.cards import (
    apply_custom_styles,
    get_priority_badge_html,
    get_status_badge_html,
    render_admin_banner,
)
from backend.database.connection import get_connection
from backend.services.maps_service import geocode_location
from backend.services.shelter_map_service import create_shelter_allocation_map

API_BASE_URL = "http://localhost:8000/emergency"

# Inject styling
apply_custom_styles()

render_admin_banner(
    title="Mission Review & Human Approval Command",
    subtitle="Inspect autonomous multi-agent operational proposals, verify RAG SOPs, and execute Human-in-the-Loop dispatch decisions.",
)


def load_all_missions():
    """Load all missions with incident details from SQLite database."""
    with get_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT m.mission_id, m.incident_id, m.status AS mission_status,
                   m.assessment_data, m.approval_status, m.rescue_plan_data,
                   m.created_at, m.updated_at,
                   i.reporter_name, i.phone, i.disaster_type, i.location,
                   i.people_affected, i.description, i.priority, i.severity_score,
                   i.resources
            FROM missions m
            LEFT JOIN incidents i ON m.incident_id = i.id
            ORDER BY m.mission_id DESC
            """,
            conn,
        )
    return df


def apply_decision(mission_id: int, action: str, payload: dict = None):
    """Execute approval, rejection, replanning, or completion via FastAPI endpoint."""
    url = f"{API_BASE_URL}/missions/{mission_id}/{action}"
    response = requests.post(url, json=payload, timeout=45)
    response.raise_for_status()
    return response.json()


# Load missions
try:
    missions_df = load_all_missions()
except Exception as err:
    st.error(f"Failed to load mission records from database: {err}")
    st.stop()

if missions_df.empty:
    st.info("No mission records found in the system. When an incident is reported, an autonomous mission proposal will appear here.")
    st.stop()

# --- Filter Bar ---
filter_c1, filter_c2, filter_c3 = st.columns([2, 3, 1])

status_filter_options = [
    "All Statuses",
    "AWAITING_APPROVAL",
    "ACTIVE",
    "REPLANNING",
    "COMPLETED",
    "REJECTED",
]
selected_status_filter = filter_c1.selectbox("Filter Mission Queue by Status", status_filter_options)

filtered_missions = missions_df.copy()
if selected_status_filter != "All Statuses":
    filtered_missions = filtered_missions[filtered_missions["mission_status"] == selected_status_filter]

# Mission Selection Dropdown
mission_options = []
mission_id_map = {}

# If an incident was just submitted, default to that mission if available
default_idx = 0
target_mission_id = None
if "latest_incident_result" in st.session_state:
    target_mission_id = st.session_state["latest_incident_result"].get("mission_id")

for idx, row in filtered_missions.iterrows():
    m_id = row["mission_id"]
    label = f"Mission #{m_id} — {row['disaster_type']} ({row['location']}) [{row['mission_status']}]"
    mission_options.append(label)
    mission_id_map[label] = row
    if target_mission_id and m_id == target_mission_id:
        default_idx = len(mission_options) - 1

if not mission_options:
    st.info(f"No missions currently match the status '{selected_status_filter}'.")
    st.stop()

selected_label = filter_c2.selectbox("Select Mission to Review", mission_options, index=default_idx)
selected_row = mission_id_map[selected_label]

with filter_c3:
    st.write("")
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

st.markdown("---")

# Parse mission data
mission_id = int(selected_row["mission_id"])
incident_id = int(selected_row["incident_id"]) if pd.notna(selected_row["incident_id"]) else "N/A"
mission_status = str(selected_row["mission_status"])
approval_status = str(selected_row["approval_status"])
disaster_type = str(selected_row["disaster_type"])
location = str(selected_row["location"])
people_affected = int(selected_row["people_affected"]) if pd.notna(selected_row["people_affected"]) else 1

plan_data = {}
if selected_row.get("rescue_plan_data"):
    try:
        plan_data = json.loads(selected_row["rescue_plan_data"])
    except Exception:
        pass

assessment_data = {}
if selected_row.get("assessment_data"):
    try:
        assessment_data = json.loads(selected_row["assessment_data"])
    except Exception:
        pass
if not assessment_data and isinstance(plan_data.get("assessment"), dict):
    assessment_data = plan_data.get("assessment")

# Priority, severity, reason, resources
priority = assessment_data.get("priority") or (str(selected_row["priority"]) if pd.notna(selected_row.get("priority")) else "MEDIUM")
severity_score = assessment_data.get("severity_score") or (int(selected_row["severity_score"]) if pd.notna(selected_row.get("severity_score")) else 50)
reason = assessment_data.get("reason", "")
if not reason and plan_data.get("risk_notes"):
    reason = "; ".join(plan_data["risk_notes"])

# Resources list
res_list = assessment_data.get("resources") or plan_data.get("required_resources") or []
if not res_list and selected_row.get("resources"):
    try:
        res_list = json.loads(selected_row["resources"])
    except Exception:
        res_list = [r.strip() for r in str(selected_row["resources"]).split(",") if r.strip()]

# RAG context
rag_context = plan_data.get("rag_context") or {}

# Hospitals
hospitals = plan_data.get("hospital_plan") or plan_data.get("hospitals") or []

# Shelters
shelters = plan_data.get("shelter_plan") or plan_data.get("shelters") or []

# Volunteers
volunteer_plan = plan_data.get("volunteer_plan") or []
volunteers_alloc = plan_data.get("volunteer_allocation") or {}

# Rescue plan (plan_data itself contains objective, response_steps, resource_gaps, risk_notes)
rescue_plan = plan_data.get("rescue_plan") or plan_data

# Communications & Reservations
communications = plan_data.get("communications") or {}
notification_dispatch = plan_data.get("notification_dispatch") or {}
shelter_reservation = plan_data.get("shelter_reservation") or {}
reflection = plan_data.get("reflection") or {}

# Model Attribution Logic
is_fallback = "deterministic severity score" in reason.lower() or reason.startswith("Automated assessment for")
if is_fallback:
    model_badge_html = '<span class="model-pill fallback">⚙️ Domain Rule Engine (Deterministic Fallback)</span>'
else:
    model_badge_html = '<span class="model-pill ollama">🦙 Local Ollama (qwen2.5:7b)</span>'

# Header Overview Card
st.markdown(
    f"""
    <div style="background: #FFFFFF; border: 1px solid #CFD8DC; border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #ECEFF1; padding-bottom: 0.75rem; margin-bottom: 1rem;">
            <div>
                <span style="font-size: 0.8rem; font-weight: 700; color: #1976D2; text-transform: uppercase; letter-spacing: 1px;">Human-in-the-Loop Operations Console</span>
                <h2 style="margin: 0.2rem 0; color: #263238; font-size: 1.6rem; font-weight: 800;">
                    Mission #{mission_id} &nbsp;•&nbsp; Incident #{incident_id} ({disaster_type} at {location})
                </h2>
            </div>
            <div style="display: flex; gap: 0.5rem; align-items: center;">
                {get_priority_badge_html(priority)}
                {get_status_badge_html(mission_status)}
            </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;">
            <div>
                <div style="font-size: 0.75rem; text-transform: uppercase; color: #546E7A; font-weight: 600;">People Affected</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: #263238;">{people_affected:,} Persons</div>
            </div>
            <div>
                <div style="font-size: 0.75rem; text-transform: uppercase; color: #546E7A; font-weight: 600;">Reporter Contact</div>
                <div style="font-size: 1.05rem; font-weight: 600; color: #37474F;">{selected_row['reporter_name']} ({selected_row['phone']})</div>
            </div>
            <div>
                <div style="font-size: 0.75rem; text-transform: uppercase; color: #546E7A; font-weight: 600;">Approval Status</div>
                <div style="font-size: 1.1rem; font-weight: 700; color: #1976D2;">{approval_status}</div>
            </div>
            <div>
                <div style="font-size: 0.75rem; text-transform: uppercase; color: #546E7A; font-weight: 600;">AI Engine Attribution</div>
                <div style="margin-top: 0.2rem;">{model_badge_html}</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Incident Description Box
with st.expander("📝 Incident Distress Details & Citizen Description", expanded=True):
    st.write(f"**Description:** {selected_row['description']}")
    st.caption(f"Reported at: {selected_row['created_at']} | Last Updated: {selected_row['updated_at']}")

# Operational Tabs
tab_assessment, tab_rag, tab_hospitals, tab_shelters, tab_volunteers, tab_plan, tab_comms = st.tabs([
    "🧠 AI Assessment",
    "📚 Agentic RAG SOP",
    "🏥 Hospital Network",
    "🏠 Shelter Allocation",
    "👥 Volunteer Force",
    "📋 Rescue Plan",
    "📨 Communications Dispatch",
])

with tab_assessment:
    st.subheader("Autonomous Incident Assessment")
    st.markdown(f"**Engine Attribution:** {model_badge_html}", unsafe_allow_html=True)

    a_col1, a_col2 = st.columns([1, 2])
    with a_col1:
        st.metric("Priority Level", priority)
        st.metric("Severity Score (0-100)", f"{severity_score} / 100")
        try:
            st.progress(min(1.0, max(0.0, float(severity_score) / 100.0)))
        except Exception:
            pass

    with a_col2:
        st.markdown("**Required Rescue Resources:**")
        if res_list:
            res_cols = st.columns(min(len(res_list), 3))
            for idx, r in enumerate(res_list):
                r_lower = r.lower()
                icon = "🚨"
                if "boat" in r_lower:
                    icon = "🚤"
                elif "rescue" in r_lower:
                    icon = "🧑‍🚒"
                elif "ambulance" in r_lower:
                    icon = "🚑"
                elif "medical" in r_lower:
                    icon = "🏥"
                elif "fire" in r_lower:
                    icon = "🚒"
                elif "excavator" in r_lower or "machinery" in r_lower:
                    icon = "🚜"
                elif "relief" in r_lower or "food" in r_lower or "water" in r_lower:
                    icon = "📦"
                elif "evacuation" in r_lower:
                    icon = "🏃"
                with res_cols[idx % len(res_cols)]:
                    st.success(f"{icon} **{r}**")
        else:
            st.info("No specialized heavy equipment required.")

        st.markdown("**Assessment Rationale:**")
        st.info(reason or "Standard automated triage completed.")

with tab_rag:
    st.subheader("Agentic RAG Context & SOP Verification")
    if rag_context:
        sufficient = rag_context.get("sufficient", False)
        sources = rag_context.get("sources", [])
        r_reason = rag_context.get("reason", "Standard procedure.")
        context_text = rag_context.get("context", "")

        rag_c1, rag_c2 = st.columns(2)
        rag_c1.metric("Guidance Sufficient?", "YES (Valid SOP)" if sufficient else "NO (Gaps Detected)")
        rag_c2.metric("Retrieved Sources Count", len(sources))

        st.markdown("**Retrieved Standard Operating Procedure (SOP) Documents:**")
        if sources:
            for s in sources:
                st.markdown(f"- 📄 `{s}`")
        else:
            st.caption("No external documents referenced.")

        st.markdown("**Retrieval Reasoning:**")
        st.write(r_reason)

        if context_text:
            with st.expander("📖 Inspect Full Retrieved RAG Context & Domain SOPs", expanded=False):
                st.text(context_text)
    else:
        st.info("RAG context is not recorded for this mission record.")

with tab_hospitals:
    st.subheader("🏥 Hospital Routing & Medical Facilities")
    if hospitals:
        h_rows = []
        for h in hospitals:
            dist = h.get("distance_km") if h.get("distance_km") is not None else h.get("straight_distance_km")
            dist_str = f"{dist:.2f} km" if dist is not None else "N/A"
            h_rows.append({
                "Hospital Name": h.get("name"),
                "District": h.get("district"),
                "Facility Type": h.get("hospital_type", "General"),
                "Distance": dist_str,
                "Emergency Phone": h.get("phone") or h.get("contact", "N/A"),
                "Specialties / Trauma Units": h.get("specialties", "Emergency / Trauma"),
            })
        st.dataframe(pd.DataFrame(h_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No nearby hospital routing was allocated for this incident.")

with tab_shelters:
    st.subheader("🏠 Shelter Allocation & Real-Time Capacity")
    if shelters:
        primary_shelter = shelters[0] if isinstance(shelters, list) and len(shelters) > 0 else {}
        sh_col1, sh_col2, sh_col3, sh_col4 = st.columns(4)
        sh_col1.metric("Primary Safe Shelter", primary_shelter.get("name", "N/A"))
        sh_col2.metric("District", primary_shelter.get("district", "N/A"))
        avail_cap = primary_shelter.get("available_capacity")
        if avail_cap is None:
            avail_cap = max(0, primary_shelter.get("capacity", 0) - primary_shelter.get("occupancy", 0))
        sh_col3.metric("Available Capacity", f"{avail_cap:,} people")
        dist = primary_shelter.get("distance_km")
        sh_col4.metric("Distance", f"{dist:.1f} km" if dist is not None else "Local")

        st.markdown("#### Suitable Alternative Shelters")
        s_rows = []
        for s in shelters:
            s_avail = s.get("available_capacity")
            if s_avail is None:
                s_avail = max(0, s.get("capacity", 0) - s.get("occupancy", 0))
            s_dist = s.get("distance_km")
            s_rows.append({
                "Shelter Name": s.get("name"),
                "District": s.get("district"),
                "Total Capacity": s.get("capacity"),
                "Occupancy": s.get("occupancy"),
                "Available": s_avail,
                "Distance (km)": f"{s_dist:.1f}" if s_dist is not None else "N/A",
                "Suitability Score": f"{s.get('suitability_score', 0.0):.1f}" if s.get("suitability_score") is not None else "N/A",
                "Contact": s.get("contact", "N/A"),
            })
        st.dataframe(pd.DataFrame(s_rows), use_container_width=True, hide_index=True)

        # Shelter Map
        st.markdown("#### 🗺️ Geographic Allocation Map")
        coords = plan_data.get("incident_coordinates")
        if not coords:
            coords = geocode_location(location)
        if coords:
            m = create_shelter_allocation_map(coords, shelters)
            if m:
                st_folium(m, width=None, height=450, key=f"admin_folium_map_{mission_id}")
            else:
                st.info("Shelter map rendering unavailable.")
        else:
            st.caption(f"Coordinates could not be resolved for '{location}'.")
    else:
        st.info("No shelters found in database matching capacity criteria.")

with tab_volunteers:
    st.subheader("👥 Volunteer Force Matching & Skill Specialization")
    v_assigned = []
    v_unmet = []

    if isinstance(volunteer_plan, list) and len(volunteer_plan) > 0:
        v_assigned = volunteer_plan
    elif isinstance(volunteers_alloc, dict):
        v_assigned = volunteers_alloc.get("assigned_volunteers") or volunteers_alloc.get("assignments") or []
        v_unmet = volunteers_alloc.get("unmet_skills") or []
    
    if not v_unmet:
        v_unmet = plan_data.get("resource_gaps") or rescue_plan.get("resource_gaps") or []

    if v_assigned or v_unmet:
        v_c1, v_c2, v_c3 = st.columns(3)
        v_c1.metric("Allocation Status", "✅ Fully Staffed" if not v_unmet else "⚠️ Resource Gap Detected")
        v_c2.metric("Volunteers Deployed", len(v_assigned))
        v_c3.metric("Unmet Skill Demands", len(v_unmet))

        if v_unmet:
            st.warning(f"⚠️ Unmet Volunteer Specializations / Shortfalls: {', '.join([str(g) for g in v_unmet])}")

        if v_assigned:
            st.markdown("#### Deployed Personnel Roster")
            va_rows = []
            for v in v_assigned:
                va_rows.append({
                    "Volunteer Name": v.get("volunteer_name") or v.get("name", "Volunteer"),
                    "District": v.get("volunteer_district") or v.get("district", "N/A"),
                    "Matched Skill / Role": v.get("required_skill") or v.get("matched_skill") or v.get("volunteer_skills") or v.get("skills", "General Relief"),
                    "Contact Phone / Email": v.get("volunteer_contact") or v.get("contact", "N/A"),
                    "Status": str(v.get("assignment_status", "assigned")).upper(),
                })
            st.dataframe(pd.DataFrame(va_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No volunteer assignments recorded.")
    else:
        st.info("Volunteer allocation data not present.")

with tab_plan:
    st.subheader("📋 Operational Rescue Plan")
    if rescue_plan:
        st.markdown(f"**Strategic Objective:** {rescue_plan.get('objective', 'Immediate victim safety and triage.')}")

        steps = rescue_plan.get("response_steps") or rescue_plan.get("steps") or rescue_plan.get("tactical_action_steps") or []
        if steps:
            st.markdown("#### Tactical Action Steps:")
            for i, step in enumerate(steps, 1):
                st.markdown(f"**{i}.** {step}")
        else:
            st.info("Action steps are being prepared.")

        gaps = rescue_plan.get("resource_gaps") or []
        if gaps:
            st.markdown("#### ⚠️ Identified Resource Shortfalls:")
            for gap in gaps:
                st.markdown(f"- 🔴 {gap}")

        risks = rescue_plan.get("risk_notes") or rescue_plan.get("safety_warnings") or rescue_plan.get("risks") or []
        if risks:
            st.markdown("#### 🛡️ Responder Safety Protocol:")
            for risk in risks:
                st.markdown(f"- ⚠️ {risk}")
    else:
        st.info("Rescue plan has not been generated for this mission.")

with tab_comms:
    st.subheader("📨 Emergency Communications & Resend Dispatch Log")
    dispatch_mode = notification_dispatch.get("dispatch_mode") or plan_data.get("dispatch_mode", "DRY_RUN")

    c_m1, c_m2, c_m3 = st.columns(3)
    c_m1.metric("Notification Mode", dispatch_mode)
    c_m2.metric("Live Emails Submitted", notification_dispatch.get("sent") or notification_dispatch.get("submitted", 0))
    c_m3.metric("Simulated / Dry-Run", notification_dispatch.get("simulated", 0))

    if dispatch_mode == "DRY_RUN":
        st.info("🧪 System in DRY_RUN Mode: Email delivery to Resend was safely simulated without external transmission.")
    else:
        st.success("🟢 System in LIVE Mode: Email dispatches transmitted via Resend API.")

    dispatch_results = notification_dispatch.get("results") or []
    if dispatch_results:
        st.markdown("#### Dispatch Message Ledger")
        d_rows = []
        for d in dispatch_results:
            d_rows.append({
                "Channel": d.get("channel", "email"),
                "Recipient": d.get("recipient", "N/A"),
                "Subject": d.get("subject", ""),
                "Dispatch Status": str(d.get("status", "")).upper(),
                "Note / ID": d.get("id") or d.get("reason") or d.get("error") or "",
            })
        st.dataframe(pd.DataFrame(d_rows), use_container_width=True, hide_index=True)
    elif communications:
        messages = communications.get("messages", [])
        if messages:
            st.markdown("#### Prepared Notification Messages")
            for msg in messages:
                st.markdown(f"- **[{msg.get('target', '').upper()}]** `{msg.get('recipient')}` via `{msg.get('channel')}`: *{msg.get('subject')}*")


# ==============================================================================
# SECTION: HUMAN-IN-THE-LOOP APPROVAL BOUNDARY CONTROLS
# ==============================================================================
st.markdown("---")
st.subheader("⚡ Human-in-the-Loop Decision Console")

if approval_status == "PENDING" or mission_status == "AWAITING_APPROVAL":
    st.warning("⚠️ This autonomous mission is awaiting mandatory coordinator authorization before field units are dispatched.")

    rejection_feedback = st.text_input(
        "Optional Reviewer Feedback / Instructions (used if rejecting for strategic replanning):",
        key=f"rejection_feedback_input_{mission_id}",
    )

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("🟢 APPROVE & DISPATCH MISSION", type="primary", use_container_width=True, key=f"btn_approve_{mission_id}"):
            with st.spinner("Authorizing mission and executing communication dispatch..."):
                try:
                    res = apply_decision(mission_id, "approve")
                    st.success(f"✅ Mission #{mission_id} APPROVED and ACTIVATED! Field resources notified.")
                    st.rerun()
                except Exception as err:
                    st.error(f"Approval failed: {err}")

    with btn_col2:
        if st.button("🔴 REJECT FOR REPLANNING", use_container_width=True, key=f"btn_reject_{mission_id}"):
            with st.spinner("Rejecting proposal and releasing reserved capacity..."):
                try:
                    payload = {"feedback": rejection_feedback} if rejection_feedback.strip() else None
                    res = apply_decision(mission_id, "reject", payload=payload)
                    st.warning(f"Mission #{mission_id} rejected. Volunteers released and marked for replanning.")
                    st.rerun()
                except Exception as err:
                    st.error(f"Rejection failed: {err}")

elif mission_status == "REPLANNING":
    st.info("🟠 This mission was rejected and is currently queued for strategic AI replanning.")

    if reflection:
        with st.expander("🔍 Strategic Reflection Insights & Diagnosis", expanded=True):
            st.write("**Summary:**", reflection.get("reflection_summary", "Replanning required."))
            st.write("**Diagnosis:**", reflection.get("diagnosis", "Strategic adjustments needed."))
            if reflection.get("human_feedback"):
                st.caption(f"Coordinator Feedback: {reflection.get('human_feedback')}")

    replan_feedback = st.text_input(
        "Additional Instructions for AI Replanning (optional):",
        key=f"replan_feedback_input_{mission_id}",
    )

    if st.button("🔄 REPLAN MISSION NOW", type="primary", use_container_width=True, key=f"btn_replan_{mission_id}"):
        with st.spinner("Invoking autonomous replanning agent..."):
            try:
                payload = {"feedback": replan_feedback} if replan_feedback.strip() else None
                res = apply_decision(mission_id, "replan", payload=payload)
                st.success(f"Mission #{mission_id} replanned and resubmitted for human review!")
                st.rerun()
            except Exception as err:
                st.error(f"Replanning failed: {err}")

elif mission_status == "ACTIVE":
    st.success("🟢 Mission is ACTIVE. Field teams are deployed, shelter capacity is reserved, and communications have been dispatched.")

    if shelter_reservation:
        st.info(f"🏠 Active Shelter Reservation: **{shelter_reservation.get('shelter_name')}** ({shelter_reservation.get('reserved_capacity')} persons reserved)")

    if st.button("✅ COMPLETE MISSION & RELEASE ALL RESOURCES", type="primary", use_container_width=True, key=f"btn_complete_{mission_id}"):
        with st.spinner("Concluding mission and restoring volunteer & shelter capacity..."):
            try:
                res = apply_decision(mission_id, "complete")
                st.success(f"Mission #{mission_id} concluded successfully! Volunteers and shelter capacity restored.")
                st.rerun()
            except Exception as err:
                st.error(f"Completion failed: {err}")

elif mission_status == "COMPLETED":
    st.success(f"✅ Mission #{mission_id} is COMPLETED. All relief assignments concluded and shelter capacity released.")

elif mission_status == "REJECTED":
    st.error(f"🔴 Mission #{mission_id} was REJECTED.")

