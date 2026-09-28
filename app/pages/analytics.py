import pandas as pd
import streamlit as st

from app.components.cards import apply_custom_styles, render_admin_banner
from backend.database.connection import get_connection

apply_custom_styles()

render_admin_banner(
    title="Disaster Response & Resource Analytics",
    subtitle="Statewide resource capacity analysis, district shelter occupancy trends, and hospital distribution metrics.",
)

def load_shelter_data():
    """Return shelter capacity and occupancy data from the existing database."""
    with get_connection() as connection:
        return pd.read_sql_query(
            """
            SELECT id, name, district, capacity, occupancy, contact
            FROM shelters
            ORDER BY district, name
            """,
            connection,
        )


def load_hospital_data():
    """Return the existing hospital resource dataset when it is available."""
    with get_connection() as connection:
        return pd.read_sql_query(
            "SELECT name, district, hospital_type FROM hospitals",
            connection,
        )


try:
    shelters = load_shelter_data()
except Exception as error:
    st.error(f"Unable to load shelter analytics: {error}")
    st.stop()

if shelters.empty:
    st.info("No shelter data is currently available.")
    st.stop()

shelters["occupancy"] = shelters["occupancy"].fillna(0)
shelters["available_capacity"] = (
    shelters["capacity"] - shelters["occupancy"]
).clip(lower=0)
shelters["utilization_percent"] = (
    shelters["occupancy"].div(shelters["capacity"].replace(0, pd.NA)) * 100
).fillna(0).round(1)

total_capacity = int(shelters["capacity"].sum())
current_occupancy = int(shelters["occupancy"].sum())
available_capacity = int(shelters["available_capacity"].sum())
average_occupancy_rate = (
    current_occupancy / total_capacity * 100 if total_capacity else 0
)

st.subheader("Shelter Summary")
metric_columns = st.columns(5)
metric_columns[0].metric("Total Shelters", len(shelters))
metric_columns[1].metric("Total Capacity", f"{total_capacity:,}")
metric_columns[2].metric("Current Occupancy", f"{current_occupancy:,}")
metric_columns[3].metric("Available Capacity", f"{available_capacity:,}")
metric_columns[4].metric("Average Occupancy Rate", f"{average_occupancy_rate:.1f}%")

district_summary = (
    shelters.groupby("district", as_index=False)
    .agg(
        shelters=("id", "count"),
        total_capacity=("capacity", "sum"),
        occupancy=("occupancy", "sum"),
        available_capacity=("available_capacity", "sum"),
    )
    .sort_values("district")
)
district_summary["occupancy_rate_percent"] = (
    district_summary["occupancy"].div(
        district_summary["total_capacity"].replace(0, pd.NA)
    )
    * 100
).fillna(0).round(1)

st.divider()
st.subheader("District Shelter Analytics")
st.dataframe(district_summary, use_container_width=True, hide_index=True)
st.bar_chart(
    district_summary.set_index("district")[["total_capacity", "available_capacity"]],
    use_container_width=True,
)

st.divider()
st.subheader("Shelter Utilization")
utilization_columns = [
    "name",
    "district",
    "capacity",
    "occupancy",
    "available_capacity",
    "utilization_percent",
    "contact",
]
st.dataframe(
    shelters[utilization_columns].sort_values(
        ["utilization_percent", "occupancy"], ascending=False
    ),
    use_container_width=True,
    hide_index=True,
)

high_occupancy = shelters[shelters["utilization_percent"] >= 80]
if high_occupancy.empty:
    st.info("No shelters are currently at or above 80% occupancy.")
else:
    st.warning("Shelters at or above 80% occupancy")
    st.dataframe(
        high_occupancy[utilization_columns].sort_values(
            "utilization_percent", ascending=False
        ),
        use_container_width=True,
        hide_index=True,
    )

st.divider()
st.subheader("Resource Analytics")
try:
    hospitals = load_hospital_data()
except Exception:
    hospitals = pd.DataFrame()

if hospitals.empty:
    st.info("Resource analytics are not currently available from existing data.")
else:
    st.caption(
        "Hospital records are available. Live resource capacity and availability "
        "are not currently tracked."
    )
    resource_columns = st.columns(2)
    resource_columns[0].metric("Registered Hospitals", len(hospitals))
    resource_columns[1].metric(
        "Districts with Hospitals", hospitals["district"].nunique()
    )
    hospital_summary = (
        hospitals.groupby("district", as_index=False)
        .agg(hospitals=("name", "count"))
        .sort_values("district")
    )
    st.dataframe(hospital_summary, use_container_width=True, hide_index=True)
