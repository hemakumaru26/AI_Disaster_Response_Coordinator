import json
import streamlit as st

from app.components.cards import (
    apply_custom_styles,
    render_user_banner,
    render_user_incident_card,
)
from backend.database.connection import get_connection

apply_custom_styles()

render_user_banner(
    title="Track Incident & Rescue Status",
    subtitle="Check live status, assigned relief resources, safe shelters, and response times for your report.",
)

# Search Input
col_s1, col_s2 = st.columns([3, 1])
with col_s1:
    default_id = ""
    if "latest_incident_result" in st.session_state:
        default_id = str(st.session_state["latest_incident_result"].get("incident_id", ""))
    incident_query = st.text_input("Enter Incident Tracking ID", value=default_id, placeholder="e.g. 101 or 120")
with col_s2:
    st.write("")
    search_btn = st.button("🔍 Check Status", use_container_width=True)


def lookup_incident_status(incident_id: int):
    """Retrieve non-technical operational status for a citizen report."""
    with get_connection() as conn:
        inc_row = conn.execute(
            "SELECT * FROM incidents WHERE id = ?", (incident_id,)
        ).fetchone()

        if not inc_row:
            return None, None

        mission_row = conn.execute(
            "SELECT * FROM missions WHERE incident_id = ? ORDER BY mission_id DESC LIMIT 1",
            (incident_id,),
        ).fetchone()

    inc_dict = dict(inc_row)
    resources_list = []
    if inc_dict.get("resources"):
        try:
            resources_list = json.loads(inc_dict["resources"])
        except Exception:
            resources_list = [r.strip() for r in str(inc_dict["resources"]).split(",") if r.strip()]

    # Extract mission data
    workflow_dict = {}
    nearest_shelters = []
    if mission_row:
        m_dict = dict(mission_row)
        plan_data = {}
        if m_dict.get("rescue_plan_data"):
            try:
                plan_data = json.loads(m_dict["rescue_plan_data"])
            except Exception:
                pass

        shelters = plan_data.get("shelters") or []
        if shelters:
            nearest_shelters = shelters

        workflow_dict = {
            "mission_id": m_dict.get("mission_id"),
            "status": m_dict.get("status", "AWAITING_APPROVAL"),
            "approval_status": m_dict.get("approval_status", "PENDING"),
            "shelters": nearest_shelters,
            "rescue_plan": plan_data.get("rescue_plan") or {},
            "communications": plan_data.get("communications") or {},
        }
    else:
        workflow_dict = {
            "status": "AWAITING_APPROVAL",
            "approval_status": "PENDING",
            "shelters": [],
            "rescue_plan": {},
        }

    card_result = {
        "incident_id": inc_dict.get("id"),
        "assessment": {
            "priority": inc_dict.get("priority", "HIGH"),
            "severity_score": inc_dict.get("severity_score", 50),
            "resources": resources_list,
        },
        "nearest_shelters": nearest_shelters,
        "workflow": workflow_dict,
        "workflow_status": workflow_dict.get("status"),
    }

    incident_details = {
        "reporter_name": inc_dict.get("reporter_name", "Citizen"),
        "disaster_type": inc_dict.get("disaster_type", "Emergency"),
        "location": inc_dict.get("location", "Tamil Nadu"),
        "people_affected": inc_dict.get("people_affected", 1),
        "description": inc_dict.get("description", ""),
    }

    return card_result, incident_details


if incident_query.strip():
    try:
        inc_id = int(incident_query.strip())
        res, details = lookup_incident_status(inc_id)
        if res:
            render_user_incident_card(res, details)
        else:
            st.warning(f"No incident report found with Tracking ID #{inc_id}. Please verify your ID or submit a new emergency report.")
    except ValueError:
        st.error("Please enter a valid numeric Incident ID (e.g. 101).")
else:
    st.info("💡 Enter your Incident Tracking ID above to view live operational status and relief updates.")

