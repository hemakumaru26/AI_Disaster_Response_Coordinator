import json
import pandas as pd
import streamlit as st

from backend.database.connection import get_connection

try:
    st.set_page_config(
        page_title="Shelter Management | AI Disaster Coordinator",
        page_icon="🏠",
        layout="wide",
    )
except Exception:
    pass

from app.components.cards import apply_custom_styles, render_admin_banner

apply_custom_styles()

render_admin_banner(
    title="Shelter Management & Allocation Network",
    subtitle="Live shelter capacity monitoring, district-level availability, and incident reservation lifecycle tracking.",
)


def load_shelter_data() -> pd.DataFrame:
    """Load shelter capacity, occupancy, and contact information from the database."""
    with get_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT id, name, district, address, latitude, longitude,
                   capacity, occupancy, contact
            FROM shelters
            ORDER BY district ASC, name ASC
            """,
            conn,
        )
    return df


def load_mission_reservations() -> list:
    """Extract active and completed shelter reservations from persistent mission records.
    
    Includes the reserved shelter's district by resolving shelter_id against the shelters catalog.
    """
    try:
        with get_connection() as conn:
            # Query shelters to map shelter_id -> district
            sh_rows = conn.execute("SELECT id, district FROM shelters").fetchall()
            shelter_district_map = {r["id"]: r["district"] for r in sh_rows}

            rows = conn.execute(
                """
                SELECT mission_id, incident_id, status, approval_status,
                       rescue_plan_data, updated_at
                FROM missions
                WHERE rescue_plan_data IS NOT NULL
                ORDER BY mission_id DESC
                """
            ).fetchall()
    except Exception:
        return []

    reservations = []
    for row in rows:
        try:
            plan = json.loads(row["rescue_plan_data"]) if row["rescue_plan_data"] else {}
            res = plan.get("shelter_reservation")
            if isinstance(res, dict) and res.get("shelter_id") is not None:
                s_id = res.get("shelter_id")
                reservations.append(
                    {
                        "mission_id": row["mission_id"],
                        "incident_id": row["incident_id"],
                        "shelter_id": s_id,
                        "shelter_name": res.get("shelter_name", "Shelter"),
                        "shelter_district": shelter_district_map.get(s_id, "Unknown"),
                        "reserved_capacity": res.get("reserved_capacity", 0),
                        "reservation_status": res.get("status", "unknown"),
                        "mission_status": row["status"],
                        "approval_status": row["approval_status"],
                        "updated_at": row["updated_at"],
                    }
                )
        except Exception:
            continue

    return reservations


# --- Load Data ---
try:
    shelters_raw = load_shelter_data()
except Exception as err:
    st.error(f"Unable to load shelter data from database: {err}")
    st.stop()

if shelters_raw.empty:
    st.info("No shelter data is currently registered in the database.")
    st.stop()

# --- Process Shelter Metrics ---
df = shelters_raw.copy()
df["capacity"] = df["capacity"].fillna(0).astype(int)
df["occupancy"] = df["occupancy"].fillna(0).astype(int)
df["available_capacity"] = (df["capacity"] - df["occupancy"]).clip(lower=0)
df["utilization_percent"] = (
    df["occupancy"].div(df["capacity"].replace(0, pd.NA)) * 100
).fillna(0.0).round(1)


def derive_status(row):
    cap = row["capacity"]
    occ = row["occupancy"]
    if cap <= 0:
        return "Unavailable"
    if occ >= cap:
        return "Full"
    if occ > 0:
        return "Partially Occupied"
    return "Available"


df["status"] = df.apply(derive_status, axis=1)

# --- Top Filter & Control Bar ---
st.subheader("🔍 Filter & Operational Scope")

filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([2, 2, 3, 1])

all_districts = sorted([d for d in df["district"].dropna().unique() if str(d).strip()])
district_options = ["All Districts"] + all_districts
selected_district = filter_col1.selectbox("Filter by District", district_options)

status_options = ["All Statuses", "Available", "Partially Occupied", "Full"]
selected_status = filter_col2.selectbox("Filter by Status", status_options)

search_query = filter_col3.text_input("Search Shelter Name or Address", "")

with filter_col4:
    st.write("")
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

st.markdown("---")

# --- 1. Summary Metrics Header ---
if selected_district == "All Districts":
    st.subheader("📊 System-Wide Capacity Overview")
    metric_df = df
else:
    st.subheader(f"📊 Capacity Overview — {selected_district} District")
    metric_df = df[df["district"] == selected_district]

total_shelters = len(metric_df)
total_capacity = int(metric_df["capacity"].sum())
total_occupied = int(metric_df["occupancy"].sum())
total_available = int(metric_df["available_capacity"].sum())
avg_utilization = (
    (total_occupied / total_capacity * 100) if total_capacity > 0 else 0.0
)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Shelters", f"{total_shelters:,}")
col2.metric("Total Capacity", f"{total_capacity:,}")
col3.metric("Current Occupancy", f"{total_occupied:,}")
col4.metric("Available Capacity", f"{total_available:,}")
col5.metric("Avg Utilization", f"{avg_utilization:.1f}%")

if selected_district != "All Districts":
    st.caption(
        f"🌐 **System-Wide Reference:** 380 total shelters | 367,250 total capacity | "
        f"{int(df['occupancy'].sum()):,} occupied | {int(df['available_capacity'].sum()):,} available"
    )

st.markdown("---")

# --- 2. Apply Filters to Directory ---
st.subheader("🏢 Shelter Directory")

filtered_df = df.copy()

if selected_district != "All Districts":
    filtered_df = filtered_df[filtered_df["district"] == selected_district]

if selected_status != "All Statuses":
    filtered_df = filtered_df[filtered_df["status"] == selected_status]

if search_query.strip():
    q = search_query.strip().lower()
    filtered_df = filtered_df[
        filtered_df["name"].str.lower().str.contains(q, na=False)
        | filtered_df["address"].str.lower().str.contains(q, na=False)
    ]

# Summary of Filtered Results
st.caption(
    f"Showing **{len(filtered_df)}** of **{len(df)}** shelters "
    f"| Filtered Capacity: **{filtered_df['capacity'].sum():,}** "
    f"| Filtered Available: **{filtered_df['available_capacity'].sum():,}**"
)

# --- 4. District Breakdown Table (Expander) ---
with st.expander("📊 District-Level Shelter Summary Breakdown", expanded=False):
    district_agg = (
        df.groupby("district", as_index=False)
        .agg(
            total_shelters=("id", "count"),
            total_capacity=("capacity", "sum"),
            occupied_capacity=("occupancy", "sum"),
            available_capacity=("available_capacity", "sum"),
        )
        .sort_values(by="district")
    )
    district_agg["avg_occupancy_rate"] = (
        district_agg["occupied_capacity"]
        .div(district_agg["total_capacity"].replace(0, pd.NA))
        .mul(100)
        .fillna(0.0)
        .round(1)
        .astype(str)
        + "%"
    )
    st.dataframe(
        district_agg.rename(
            columns={
                "district": "District",
                "total_shelters": "Shelters",
                "total_capacity": "Total Capacity",
                "occupied_capacity": "Occupied",
                "available_capacity": "Available",
                "avg_occupancy_rate": "Utilization Rate",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

# --- 5. Main Shelter Table ---
display_cols = [
    "id",
    "name",
    "district",
    "capacity",
    "occupancy",
    "available_capacity",
    "utilization_percent",
    "status",
    "contact",
]

table_df = filtered_df[display_cols].rename(
    columns={
        "id": "Shelter ID",
        "name": "Shelter Name",
        "district": "District",
        "capacity": "Capacity",
        "occupancy": "Occupancy",
        "available_capacity": "Available Capacity",
        "utilization_percent": "Utilization (%)",
        "status": "Status",
        "contact": "Contact",
    }
)

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Utilization (%)": st.column_config.ProgressColumn(
            "Utilization (%)",
            help="Current occupancy as a percentage of total shelter capacity",
            format="%.1f%%",
            min_value=0,
            max_value=100,
        ),
        "Capacity": st.column_config.NumberColumn(format="%d"),
        "Occupancy": st.column_config.NumberColumn(format="%d"),
        "Available Capacity": st.column_config.NumberColumn(format="%d"),
    },
)