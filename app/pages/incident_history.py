import streamlit as st

import streamlit as st
import pandas as pd
import os

st.title("📜 Incident History")

if os.path.exists("database/incidents.csv"):

    df = pd.read_csv("database/incidents.csv")

    st.dataframe(df, use_container_width=True)

else:

    st.info("No incidents reported yet.")

st.table(
    {
        "Incident ID": [],
        "Disaster": [],
        "Location": [],
        "Priority": [],
        "Status": []
    }
)