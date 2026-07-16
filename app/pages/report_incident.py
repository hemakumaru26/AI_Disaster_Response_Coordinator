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

        try:

            response = requests.post(
                "http://127.0.0.1:8000/emergency/report",
                json=payload,
                timeout=30
            )

            response.raise_for_status()

            result = response.json()

            assessment = result["assessment"]

            st.success("✅ Emergency Submitted Successfully!")

            st.subheader("🤖 AI Assessment")

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "Priority",
                    assessment["priority"]
                )

                st.metric(
                    "Severity Score",
                    assessment["severity_score"]
                )

            with col2:
                st.metric(
                    "Incident ID",
                    result["incident_id"]
                )

                st.metric(
                    "People Affected",
                    people
                )

            st.divider()

            st.subheader("🚑 Recommended Resources")

            if assessment["resources"]:

                for resource in assessment["resources"]:
                    st.success(resource)

            else:
                st.info("No special resources required.")

            st.divider()

            st.subheader("🧠 AI Explanation")

            st.info(
                assessment["reason"]
            )

        except requests.exceptions.ConnectionError:

            st.error(
                "❌ Unable to connect to FastAPI server.\n\n"
                "Please start the backend first."
            )

        except requests.exceptions.Timeout:

            st.error(
                "❌ Request timed out while waiting for AI response."
            )

        except Exception as e:

            st.error(
                f"Unexpected Error:\n\n{e}"
            )