import streamlit as st
import pandas as pd

st.title("📊 Disaster Dashboard")

import os

if os.path.exists("database/incidents.csv"):

    df = pd.read_csv("database/incidents.csv")

else:

    df = pd.DataFrame(
        columns=[
            "reporter",
            "disaster",
            "location",
            "priority",
            "status"
        ]
    )

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("🚨 Incidents", len(df))

with col2:
    st.metric("🏥 Hospitals", 18)

with col3:
    st.metric("🏠 Shelters", 34)

with col4:
    st.metric("🙋 Volunteers", 62)

st.divider()

st.subheader("Recent Incidents")

st.dataframe(df, use_container_width=True)

st.divider()

st.subheader("Priority Distribution")

priority = df["priority"].value_counts()

st.bar_chart(priority)