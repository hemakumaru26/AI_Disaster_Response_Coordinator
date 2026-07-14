import streamlit as st
import requests

st.title("📊 Disaster Dashboard")

response = requests.get(
    "http://127.0.0.1:8000/emergency/dashboard"
)

if response.status_code == 200:

    stats = response.json()

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Incidents",
        stats["total"]
    )

    col2.metric(
        "Critical",
        stats["critical"]
    )

    col3.metric(
        "Active",
        stats["active"]
    )

else:

    st.error("Dashboard unavailable.")