import streamlit as st
import pandas as pd
import requests

st.title("📜 Incident History")

response = requests.get(
    "http://127.0.0.1:8000/emergency/history"
)

if response.status_code == 200:

    incidents = response.json()

    if incidents:

        df = pd.DataFrame(incidents)

        st.dataframe(
            df,
            use_container_width=True
        )

    else:

        st.info("No incidents available.")

else:

    st.error("Unable to fetch incident history.")