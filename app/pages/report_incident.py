import requests
import streamlit as st
from streamlit_folium import st_folium

from app.components.cards import apply_custom_styles, render_user_banner
from backend.services.maps_service import geocode_location
from backend.services.shelter_map_service import create_shelter_allocation_map

API_BASE_URL = "http://localhost:8000/emergency"

# Inject modern styling
apply_custom_styles()

render_user_banner(
    title="Report an Emergency Incident",
    subtitle="Submit immediate distress details for rapid automated triage and rescue coordination.",
)

# Incident Intake Form
if "latest_incident_result" not in st.session_state:
    with st.form("incident_form", clear_on_submit=False):
        st.markdown("### 📋 Emergency Report Form")
        st.caption("Please fill out the following details as accurately as possible. Emergency services will be notified.")

        col1, col2 = st.columns(2)
        with col1:
            reporter_name = st.text_input("Your Full Name", placeholder="e.g. Ramesh Kumar")
            disaster_type = st.selectbox(
                "Type of Disaster / Hazard",
                ["Flood", "Cyclone", "Earthquake", "Fire", "Landslide", "Building Collapse", "Medical Emergency", "Other"],
            )
            location = st.text_input(
                "Incident Location / District",
                placeholder="e.g. Velachery, Chennai or Katpadi, Vellore",
                help="Specify your street, landmark, village, or district in Tamil Nadu",
            )
        with col2:
            phone = st.text_input("Contact Phone Number", placeholder="e.g. 9876543210")
            people = st.number_input(
                "Estimated People Affected / In Distress",
                min_value=1,
                max_value=10000,
                value=1,
                step=1,
            )

        description = st.text_area(
            "Detailed Description of the Situation",
            placeholder="Describe water levels, building condition, injuries, special medical needs (elderly, infants), etc.",
            height=100,
        )

        st.markdown(
            """
            <div style="font-size: 0.85rem; color: #78909C; margin-bottom: 0.75rem;">
                🔒 Your contact details are securely transmitted directly to the State & District Emergency Operations Centre.
            </div>
            """,
            unsafe_allow_html=True,
        )

        submit = st.form_submit_button("🚨 SUBMIT EMERGENCY DISTRESS REPORT", use_container_width=True)

    if submit:
        if not location.strip():
            st.error("Please provide the incident location or district so responders can be routed to you.")
        elif not description.strip():
            st.error("Please provide a brief description of the emergency.")
        else:
            payload = {
                "reporter_name": reporter_name.strip() or "Anonymous Citizen",
                "phone": phone.strip() or "N/A",
                "disaster_type": disaster_type,
                "location": location.strip(),
                "people_affected": int(people),
                "description": description.strip(),
            }
            with st.spinner("Transmitting emergency alert and running autonomous response triage..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/report", json=payload, timeout=60
                    )
                    response.raise_for_status()
                    st.session_state["latest_incident_result"] = response.json()
                    st.session_state["latest_incident_details"] = payload
                    st.rerun()
                except requests.exceptions.ConnectionError:
                    st.error("⚠️ Unable to reach the Emergency Coordination API. Please dial 1070 directly for emergency assistance.")
                except requests.exceptions.Timeout:
                    st.error("⚠️ Emergency request timed out. Responders are being notified via backup channels. Dial 1070.")
                except requests.RequestException as error:
                    st.error(f"⚠️ Emergency report submission failed: {error}")

else:
    result = st.session_state["latest_incident_result"]
    details = st.session_state["latest_incident_details"]
    assessment = result.get("assessment", {})
    priority = assessment.get("priority", "HIGH")
    severity = assessment.get("severity_score", 50)
    incident_id = result.get("incident_id", "N/A")
    people = details.get("people_affected", 1)

    st.success("✅ Emergency distress report received! Dispatch coordination has been initiated.")

    st.subheader("🤖 AI Assessment")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Priority", priority)
        st.metric("Severity Score", f"{severity} / 100")
    with col2:
        st.metric("Incident ID", f"#{incident_id}")
        st.metric("People Affected", f"{people:,}")

    st.divider()

    st.subheader("🚑 Recommended Resources")
    resources = assessment.get("resources", [])
    if resources:
        res_cols = st.columns(min(len(resources), 4))
        for idx, resource in enumerate(resources):
            r_lower = resource.lower()
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
                st.success(f"{icon} **{resource}**")
    else:
        st.info("No special resources required.")

    st.divider()

    st.subheader("Shelter Allocation Map")
    incident_coordinates = result.get("incident_coordinates")
    nearest_shelters = result.get("nearest_shelters") or result.get("workflow", {}).get("shelters") or []

    if not incident_coordinates and details.get("location"):
        incident_coordinates = geocode_location(details["location"])

    if incident_coordinates and nearest_shelters:
        shelter_map = create_shelter_allocation_map(
            incident_coordinates,
            nearest_shelters,
        )
        if shelter_map is not None:
            st_folium(
                shelter_map,
                width=None,
                height=500,
                key=f"shelter_map_{incident_id}",
            )
        else:
            st.info("Shelter map cannot be displayed for this incident.")
    elif result.get("shelter_map_message"):
        st.info(result["shelter_map_message"])
    else:
        st.info("No suitable shelters were found for this incident.")

    st.divider()

    st.subheader("🧠 AI Explanation")
    st.info(assessment.get("reason", "Automated assessment completed."))

    st.markdown("---")
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("📝 Report Another Emergency", use_container_width=True):
            del st.session_state["latest_incident_result"]
            if "latest_incident_details" in st.session_state:
                del st.session_state["latest_incident_details"]
            st.rerun()
    with col_btn2:
        st.markdown(
            """
            <div style="text-align: right; padding-top: 0.4rem;">
                <span style="color: #546E7A; font-size: 0.9rem;">Need immediate medical aid? </span>
                <a href="tel:108" style="color: #D32F2F; font-weight: bold; text-decoration: none;">Dial 108</a>
            </div>
            """,
            unsafe_allow_html=True,
        )
