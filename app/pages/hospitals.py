import pandas as pd
import streamlit as st

from app.components.cards import apply_custom_styles, render_admin_banner
from backend.database.connection import get_connection

apply_custom_styles()

render_admin_banner(
    title="Healthcare Facility & Hospital Coordination Network",
    subtitle="District medical triage directory, trauma centers, and direct emergency facility dispatch lines.",
)


def load_hospital_data():
    """Load hospital facilities from SQLite."""
    with get_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT id, name, district, address, latitude, longitude,
                   hospital_type, phone, specialties
            FROM hospitals
            ORDER BY district ASC, name ASC
            """,
            conn,
        )
    return df


try:
    df_hosp = load_hospital_data()
except Exception as err:
    st.error(f"Failed to load hospital records: {err}")
    st.stop()

if df_hosp.empty:
    st.info("No hospital records found in database.")
    st.stop()

# Metrics
total_hospitals = len(df_hosp)
districts_count = df_hosp["district"].nunique()
types_count = df_hosp["hospital_type"].nunique()

m1, m2, m3 = st.columns(3)
m1.metric("Registered Facilities", f"{total_hospitals:,}")
m2.metric("Districts Covered", f"{districts_count} of 38")
m3.metric("Facility Types", types_count)

st.markdown("---")

# Filter controls
f1, f2, f3 = st.columns([2, 2, 3])
all_districts = ["All Districts"] + sorted(df_hosp["district"].dropna().unique().tolist())
sel_district = f1.selectbox("Filter by District", all_districts)

all_types = ["All Types"] + sorted(df_hosp["hospital_type"].dropna().unique().tolist())
sel_type = f2.selectbox("Filter by Facility Type", all_types)

search_q = f3.text_input("Search Hospital Name or Address", "")

filtered_df = df_hosp.copy()
if sel_district != "All Districts":
    filtered_df = filtered_df[filtered_df["district"] == sel_district]

if sel_type != "All Types":
    filtered_df = filtered_df[filtered_df["hospital_type"] == sel_type]

if search_q.strip():
    q = search_q.strip().lower()
    filtered_df = filtered_df[
        filtered_df["name"].str.lower().str.contains(q, na=False)
        | filtered_df["address"].str.lower().str.contains(q, na=False)
    ]

st.subheader(f"🏥 Hospital Directory ({len(filtered_df)} facilities)")
st.dataframe(
    filtered_df.rename(columns={
        "id": "Facility ID",
        "name": "Hospital Name",
        "district": "District",
        "address": "Address",
        "hospital_type": "Facility Type",
        "phone": "Emergency Phone",
        "specialties": "Specialties / Trauma Units",
    })[["Facility ID", "Hospital Name", "District", "Facility Type", "Address", "Emergency Phone", "Specialties / Trauma Units"]],
    use_container_width=True,
    hide_index=True,
)