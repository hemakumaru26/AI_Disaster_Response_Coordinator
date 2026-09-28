"""Reusable modern UI components, cards, badges, and role presentation helpers."""

import re
from pathlib import Path
import streamlit as st

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
CSS_FILE = ASSETS_DIR / "styles.css"


def apply_custom_styles():
    """Inject custom responsive CSS into Streamlit."""
    if CSS_FILE.exists():
        with open(CSS_FILE, "r", encoding="utf-8") as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)


def get_priority_badge_html(priority: str) -> str:
    """Return an HTML priority badge pill."""
    p_upper = (priority or "MEDIUM").upper()
    if p_upper == "CRITICAL":
        cls = "badge-critical"
    elif p_upper == "HIGH":
        cls = "badge-high"
    elif p_upper == "MEDIUM":
        cls = "badge-medium"
    else:
        cls = "badge-low"
    return f'<span class="badge {cls}">{p_upper}</span>'


def get_status_badge_html(status: str) -> str:
    """Return an HTML status badge pill."""
    s_upper = (status or "UNKNOWN").upper()
    if s_upper in ("ACTIVE", "APPROVED"):
        cls = "badge-active"
        label = "🟢 Active / Dispatched"
    elif s_upper in ("COMPLETED", "RESOLVED"):
        cls = "badge-completed"
        label = "✅ Completed"
    elif s_upper == "AWAITING_APPROVAL":
        cls = "badge-pending"
        label = "🟡 Awaiting Admin Approval"
    elif s_upper == "REPLANNING":
        cls = "badge-replanning"
        label = "🟠 Being Replanned"
    elif s_upper == "REJECTED":
        cls = "badge-critical"
        label = "🔴 Requires Review"
    else:
        cls = "badge-pending"
        label = f"🟡 {s_upper.replace('_', ' ').title()}"
    return f'<span class="badge {cls}">{label}</span>'


def render_user_banner(title: str, subtitle: str = ""):
    """Render a citizen-friendly emergency portal banner."""
    st.markdown(
        f"""
        <div class="emergency-banner">
            <div>
                <h2 style="color: #FFFFFF; margin: 0; font-size: 1.6rem; font-weight: 800;">🚨 {title}</h2>
                <p style="color: #FFCDD2; margin: 0.3rem 0 0 0; font-size: 0.95rem;">{subtitle}</p>
            </div>
            <div style="background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 8px; text-align: right;">
                <div style="font-size: 0.75rem; text-transform: uppercase; color: #FFCDD2; font-weight: 700;">State Helpline</div>
                <div style="font-size: 1.4rem; font-weight: 900; color: #FFFFFF; letter-spacing: 1px;">📞 1070</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_admin_banner(title: str, subtitle: str = ""):
    """Render a coordinator-level command center banner."""
    st.markdown(
        f"""
        <div class="admin-banner">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h2 style="color: #FFFFFF; margin: 0; font-size: 1.6rem; font-weight: 800;">🛡️ {title}</h2>
                    <p style="color: #BBDEFB; margin: 0.3rem 0 0 0; font-size: 0.95rem;">{subtitle}</p>
                </div>
                <div style="background: rgba(255,255,255,0.15); padding: 0.4rem 0.9rem; border-radius: 8px; font-size: 0.85rem; font-weight: 600;">
                    Autonomous Coordinator v2.0 | DEOC Command
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_user_incident_card(result: dict, incident_details: dict):
    """Render a clean, non-technical, reassuring operational response card for citizens.
    
    Contains ZERO raw JSON, internal dictionary dumps, or coordinator approval controls.
    """
    incident_id = result.get("incident_id", "N/A")
    assessment = result.get("assessment") or {}
    priority = assessment.get("priority", "HIGH")
    disaster_type = incident_details.get("disaster_type", "Emergency")
    location = incident_details.get("location", "Tamil Nadu")
    people_affected = incident_details.get("people_affected", 1)

    workflow = result.get("workflow") or {}
    mission = workflow.get("mission") or {}
    mission_status = (
        workflow.get("status")
        or mission.get("status")
        or result.get("workflow_status")
        or "AWAITING_APPROVAL"
    )
    approval_status = workflow.get("approval_status") or mission.get("approval_status") or "PENDING"

    # Extract clean shelter name
    shelter_name = "Assigned District Relief Centre"
    shelters = workflow.get("shelters") or result.get("nearest_shelters") or []
    if shelters and isinstance(shelters, list) and len(shelters) > 0:
        first_sh = shelters[0]
        if isinstance(first_sh, dict):
            shelter_name = first_sh.get("name") or shelter_name
            district = first_sh.get("district", "")
            if district:
                shelter_name = f"{shelter_name} ({district})"

    # Extract clean rescue response
    resources = assessment.get("resources") or []
    rescue_response_str = ", ".join(resources) if resources else "Rapid Assessment & Relief Team"

    # Extract driving ETA or default
    eta_str = "15 - 25 mins"
    rescue_plan = workflow.get("rescue_plan") or {}
    if isinstance(rescue_plan, dict):
        comms = workflow.get("communications") or {}
        messages = comms.get("messages", []) if isinstance(comms, dict) else []
        for msg in messages:
            subj = str(msg.get("subject", ""))
            body = str(msg.get("body", ""))
            eta_match = re.search(r"ETA[:\s]+([0-9]+\s*(?:mins|min|minutes|hours)?)", subj + " " + body, re.I)
            if eta_match:
                eta_str = eta_match.group(1).strip()
                break

    # Determine status presentation
    if mission_status in ("ACTIVE", "APPROVED"):
        status_pill = '<span class="badge badge-active">🟢 Response Active</span>'
        status_message = "Your emergency response has been approved and relief resources are actively deployed."
        status_alert_type = "success"
    elif mission_status in ("COMPLETED",):
        status_pill = '<span class="badge badge-completed">✅ Response Completed</span>'
        status_message = "Your emergency rescue mission has been successfully completed. Safe shelter established."
        status_alert_type = "success"
    elif mission_status in ("REPLANNING",):
        status_pill = '<span class="badge badge-replanning">🟠 Response Being Replanned</span>'
        status_message = "The emergency plan is undergoing automated strategic adjustment to incorporate additional specialized resources."
        status_alert_type = "warning"
    elif mission_status in ("REJECTED",):
        status_pill = '<span class="badge badge-critical">🔴 Response Under Review</span>'
        status_message = "Incident response requires manual review by senior emergency coordinators."
        status_alert_type = "warning"
    else:  # AWAITING_APPROVAL / CREATED / PENDING
        status_pill = '<span class="badge badge-pending">🟡 Awaiting Admin Approval</span>'
        status_message = "Your emergency has been assessed and an operational response plan is prepared. A state disaster coordinator must confirm dispatch before field units move."
        status_alert_type = "info"

    # Render Card
    card_html = (
        f'<div class="response-card">'
        f'<div class="response-card-header">'
        f'<div>'
        f'<span style="font-size: 0.85rem; font-weight: 700; color: #B71C1C; text-transform: uppercase; letter-spacing: 1px;">Official Emergency Incident</span>'
        f'<h2 style="margin: 0.2rem 0; color: #263238; font-size: 1.7rem; font-weight: 800;">Incident #{incident_id} — {disaster_type} ({location})</h2>'
        f'</div>'
        f'<div>{status_pill}</div>'
        f'</div>'
        f'<div style="margin-bottom: 1.25rem;">'
        f'<div style="font-size: 0.95rem; line-height: 1.5; color: #37474F;"><strong>Current Status:</strong> {status_message}</div>'
        f'</div>'
        f'<div class="operational-grid">'
        f'<div class="grid-item"><div class="grid-item-label">📊 Priority Level</div><div class="grid-item-value">{get_priority_badge_html(priority)}</div></div>'
        f'<div class="grid-item"><div class="grid-item-label">👥 People Affected</div><div class="grid-item-value">{people_affected:,} Persons</div></div>'
        f'<div class="grid-item"><div class="grid-item-label">🧑‍🚒 Rescue Response</div><div class="grid-item-value" style="color: #D32F2F;">{rescue_response_str}</div></div>'
        f'<div class="grid-item"><div class="grid-item-label">⏱️ Estimated Arrival (ETA)</div><div class="grid-item-value" style="color: #1976D2;">{eta_str}</div></div>'
        f'<div class="grid-item" style="grid-column: span 2;"><div class="grid-item-label">🏠 Designated Safe Shelter</div><div class="grid-item-value" style="font-size: 1.05rem;">{shelter_name}</div></div>'
        f'<div class="grid-item" style="grid-column: span 2;"><div class="grid-item-label">📞 Central Emergency Helpline</div><div class="grid-item-value" style="color: #B71C1C;">1070 (State EOC) &nbsp;|&nbsp; 1077 (District Collectorate)</div></div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)

    # Citizen Safety Advisory Box
    safety_html = (
        f'<div class="safety-notice">'
        f'<h4>⚠️ Important Safety Instructions for {disaster_type}</h4>'
        f'<ul style="margin: 0.5rem 0 0 1.2rem; padding: 0;">'
        f'<li>Remain in a secure, elevated location if floodwaters or heavy winds are present.</li>'
        f'<li>Keep mobile phones charged and battery-saving modes activated.</li>'
        f'<li>Stay clear of damaged electrical poles, downed power lines, and open manholes.</li>'
        f'<li>Do not attempt to cross moving floodwaters on foot or in two-wheelers.</li>'
        f'<li>If medical assistance is required immediately, dial <strong>108</strong> directly.</li>'
        f'</ul>'
        f'</div>'
    )
    st.markdown(safety_html, unsafe_allow_html=True)


def render_kpi_card(title: str, value: str, subtitle: str = "", border_type: str = "info"):
    """Render a clean metric KPI tile."""
    st.markdown(
        f"""
        <div class="stat-card {border_type}">
            <div style="font-size: 0.8rem; text-transform: uppercase; color: #546E7A; font-weight: 700; margin-bottom: 0.35rem;">
                {title}
            </div>
            <div style="font-size: 1.8rem; font-weight: 800; color: #263238; line-height: 1.2;">
                {value}
            </div>
            {f'<div style="font-size: 0.8rem; color: #78909C; margin-top: 0.3rem;">{subtitle}</div>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )

