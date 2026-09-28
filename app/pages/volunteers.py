import pandas as pd
import streamlit as st

from app.components.cards import apply_custom_styles, render_admin_banner
from backend.models.volunteer_model import (
    add_volunteer,
    get_available_volunteers,
    get_volunteers,
    initialize_volunteer_storage,
)

apply_custom_styles()

render_admin_banner(
    title="Volunteer Force & Specialization Registry",
    subtitle="Coordinate trained emergency volunteers, track certified field specializations, and manage availability rosters.",
)

try:
    initialize_volunteer_storage()
except Exception as error:
    st.error(f"Unable to initialize volunteer storage: {error}")
    st.stop()

# Header Metrics
all_volunteers = get_volunteers()
available_volunteers = get_available_volunteers()
assigned_count = len(all_volunteers) - len(available_volunteers)

col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("Total Registered Volunteers", f"{len(all_volunteers):,}")
col_m2.metric("🟢 Available for Deployment", f"{len(available_volunteers):,}")
col_m3.metric("🔴 Active on Missions", f"{assigned_count:,}")

st.markdown("---")

# Tab navigation for Registration vs Directory
tab_dir, tab_reg = st.tabs(["📋 Volunteer Directory & Skill Search", "➕ Register New Volunteer"])

with tab_dir:
    if all_volunteers:
        df_v = pd.DataFrame(all_volunteers)

        # Filters
        f1, f2, f3 = st.columns([2, 2, 3])
        all_dists = ["All Districts"] + sorted([d for d in df_v["district"].dropna().unique() if str(d).strip()])
        sel_dist = f1.selectbox("Filter District", all_dists)

        all_stat = ["All Statuses", "available", "assigned", "unavailable"]
        sel_stat = f2.selectbox("Filter Availability", all_stat)

        search_skill = f3.text_input("Search Volunteer Name or Skill (e.g. Boat, Medical, Fire)", "")

        v_filtered = df_v.copy()
        if sel_dist != "All Districts":
            v_filtered = v_filtered[v_filtered["district"] == sel_dist]

        if sel_stat != "All Statuses":
            if "availability_status" in v_filtered.columns:
                v_filtered = v_filtered[v_filtered["availability_status"] == sel_stat]

        if search_skill.strip():
            q = search_skill.strip().lower()
            v_filtered = v_filtered[
                v_filtered["name"].str.lower().str.contains(q, na=False)
                | v_filtered["skills"].str.lower().str.contains(q, na=False)
            ]

        st.subheader(f"👥 Registered Volunteers ({len(v_filtered)} matches)")
        cols_to_show = [c for c in ["id", "name", "contact", "district", "skills", "availability_status", "availability_details"] if c in v_filtered.columns]
        st.dataframe(
            v_filtered[cols_to_show].rename(columns={
                "id": "Volunteer ID",
                "name": "Full Name",
                "contact": "Contact",
                "district": "District",
                "skills": "Specializations / Skills",
                "availability_status": "Availability",
                "availability_details": "Notes",
            }),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No volunteers registered yet.")

with tab_reg:
    st.subheader("Register New Response Volunteer")
    with st.form("volunteer_form"):
        r_c1, r_c2 = st.columns(2)
        with r_c1:
            name = st.text_input("Volunteer Full Name", placeholder="e.g. Sundar Raman")
            contact = st.text_input("Phone Number / Email", placeholder="e.g. 9444012345")
            district = st.text_input("Home District", placeholder="e.g. Chennai or Vellore")
        with r_c2:
            skills = st.text_input(
                "Skills & Certifications (comma separated)",
                placeholder="e.g. Flood Rescue, Boat Operations, First Aid, CPR",
            )
            availability_status = st.selectbox(
                "Initial Status", ["available", "unavailable"]
            )
            availability_details = st.text_input("Availability Notes (optional)", placeholder="e.g. Weekends only, night shifts")

        submit = st.form_submit_button("Register Volunteer", use_container_width=True)

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
            st.success(f"✅ Volunteer '{name}' successfully registered!")
            st.rerun()
        except ValueError as error:
            st.error(str(error))
        except Exception as error:
            st.error(f"Unable to save volunteer: {error}")
