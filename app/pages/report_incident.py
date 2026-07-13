import requests
import streamlit as st

st.title("🚨 Emergency Incident Reporting")

with st.form("incident_form"):

    reporter_name = st.text_input("Reporter Name")

    phone = st.text_input("Phone Number")

    disaster_type = st.selectbox(
        "Disaster Type",
        [
            "Flood",
            "Earthquake",
            "Cyclone",
            "Fire",
            "Landslide",
            "Other"
        ]
    )

    location = st.text_input("Location")

    people = st.number_input(
        "People Affected",
        min_value=1,
        step=1
    )

    description = st.text_area("Description")

    submit = st.form_submit_button("Submit Emergency")

    if submit:

        payload = {
            "reporter_name": reporter_name,
            "phone": phone,
            "disaster_type": disaster_type,
            "location": location,
            "people_affected": people,
            "description": description
        }

        response = requests.post(
            "http://127.0.0.1:8000/emergency/report",
            json=payload
        )

        result = response.json()

        st.success("Emergency Submitted Successfully!")

        st.subheader("📋 Incident Summary")

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Priority", result["priority"])
            st.metric("Status", result["status"])

        with col2:
            st.metric("Disaster", disaster_type)
            st.metric("People", people)

        st.divider()

        st.json(result)