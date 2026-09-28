import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

import streamlit as st
from app.components.cards import apply_custom_styles

try:
    st.set_page_config(
        page_title="AI Disaster Response Coordinator",
        page_icon="🚨",
        layout="wide",
        initial_sidebar_state="expanded",
    )
except Exception:
    pass

apply_custom_styles()

PAGES_DIR = Path(__file__).resolve().parent / "pages"

# --- Sidebar Brand & Role Selection ---
st.sidebar.markdown(
    """
    <div style="padding: 0.5rem 0 1rem 0; border-bottom: 2px solid #ECEFF1; margin-bottom: 1rem;">
        <h2 style="color: #D32F2F; margin: 0; font-size: 1.4rem; font-weight: 800;">
            🚨 AI Disaster Response
        </h2>
        <div style="font-size: 0.8rem; color: #546E7A; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
            Autonomous Command & Coordination
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

ROLE_CITIZEN = "👤 Citizen / Public User"
ROLE_ADMIN = "🛡️ Emergency Admin / Coordinator"

# Role Selector
selected_role = st.sidebar.radio(
    "Active Operational Role",
    [ROLE_CITIZEN, ROLE_ADMIN],
    index=0,
    help="Toggle between Citizen distress reporting and Emergency Coordinator Command Center.",
)

st.sidebar.markdown("---")

if selected_role == ROLE_CITIZEN:
    st.sidebar.markdown(
        """
        <div style="background: #FFEBEE; border-left: 3px solid #D32F2F; padding: 0.75rem; border-radius: 4px; margin-bottom: 1rem;">
            <strong style="color: #B71C1C; font-size: 0.85rem;">Citizen Emergency Portal</strong>
            <p style="color: #37474F; font-size: 0.8rem; margin: 0.3rem 0 0 0;">
                Report emergencies, track response status, and access statewide relief hotlines.
            </p>
        </div>
        <div style="background: #FFFFFF; border: 1px solid #CFD8DC; padding: 0.6rem; border-radius: 6px; text-align: center;">
            <div style="font-size: 0.7rem; color: #78909C; text-transform: uppercase; font-weight: 700;">24/7 State Emergency</div>
            <div style="font-size: 1.2rem; font-weight: 900; color: #D32F2F;">📞 1070</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    pages = [
        st.Page(
            str(PAGES_DIR / "report_incident.py"),
            title="Report Emergency Incident",
            icon="🚨",
            default=True,
        ),
        st.Page(
            str(PAGES_DIR / "user_status.py"),
            title="Track Response Status",
            icon="📍",
        ),
        st.Page(
            str(PAGES_DIR / "user_help.py"),
            title="Emergency Helplines & Guides",
            icon="📞",
        ),
    ]

else:
    st.sidebar.markdown(
        """
        <div style="background: #E8EAF6; border-left: 3px solid #1A237E; padding: 0.75rem; border-radius: 4px; margin-bottom: 1rem;">
            <strong style="color: #1A237E; font-size: 0.85rem;">DEOC Command Center</strong>
            <p style="color: #37474F; font-size: 0.8rem; margin: 0.3rem 0 0 0;">
                Autonomous multi-agent triage, RAG SOPs, and Human-in-the-Loop authorization.
            </p>
        </div>
        <div style="background: #E3F2FD; border: 1px solid #BBDEFB; padding: 0.4rem; border-radius: 6px; text-align: center; font-size: 0.75rem; font-weight: 700; color: #0D47A1;">
            🛡️ Authorized Coordinator Access
        </div>
        """,
        unsafe_allow_html=True,
    )

    pages = [
        st.Page(
            str(PAGES_DIR / "dashboard.py"),
            title="Command Center Overview",
            icon="📊",
            default=True,
        ),
        st.Page(
            str(PAGES_DIR / "admin_missions.py"),
            title="Mission Review & HITL Approval",
            icon="📋",
        ),
        st.Page(
            str(PAGES_DIR / "incident_history.py"),
            title="Incident Queue & Audit",
            icon="🚨",
        ),
        st.Page(
            str(PAGES_DIR / "shelters.py"),
            title="Shelter Network & Capacity",
            icon="🏠",
        ),
        st.Page(
            str(PAGES_DIR / "hospitals.py"),
            title="Hospital Coordination Network",
            icon="🏥",
        ),
        st.Page(
            str(PAGES_DIR / "volunteers.py"),
            title="Volunteer Force & Skills",
            icon="👥",
        ),
        st.Page(
            str(PAGES_DIR / "admin_communications.py"),
            title="Communications Dispatch Log",
            icon="📨",
        ),
        st.Page(
            str(PAGES_DIR / "analytics.py"),
            title="Operational Analytics",
            icon="📈",
        ),
        st.Page(
            str(PAGES_DIR / "settings.py"),
            title="System Health & Diagnostics",
            icon="⚙️",
        ),
    ]

# Navigation Execution
nav = st.navigation(pages)
nav.run()