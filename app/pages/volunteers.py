import pandas as pd
import streamlit as st

from backend.models.volunteer_model import (
    add_volunteer,
    get_available_volunteers,
    get_volunteers,
    initialize_volunteer_storage,
)

st.title("🙋 Volunteer Management")

try:
    initialize_volunteer_storage()
except Exception as error:
    st.error(f"Unable to initialize volunteer storage: {error}")
    st.stop()

with st.form("volunteer_form"):
    name = st.text_input("Volunteer Name")
    contact = st.text_input("Contact Information")
    district = st.text_input("District")
    skills = st.text_input("Skills / Specialization")
    availability_status = st.selectbox(
        "Availability Status", ["available", "unavailable"]
    )
    availability_details = st.text_area("Availability Notes (optional)")
    submit = st.form_submit_button("Save Volunteer")

if submit:
    try:
        add_volunteer(
            name=name,
            contact=contact,
            district=district,
            skills=skills,
            availability_status=availability_status,
            availability_details=availability_details,
        )
        st.success("Volunteer saved successfully.")
    except ValueError as error:
        st.error(str(error))
    except Exception as error:
        st.error(f"Unable to save volunteer: {error}")

all_volunteers = get_volunteers()
available_volunteers = get_available_volunteers()

metric_columns = st.columns(2)
metric_columns[0].metric("Registered Volunteers", len(all_volunteers))
metric_columns[1].metric("Available Volunteers", len(available_volunteers))

if all_volunteers:
    st.subheader("Volunteer Availability")
    st.dataframe(
        pd.DataFrame(all_volunteers),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No volunteers have been registered yet.")
