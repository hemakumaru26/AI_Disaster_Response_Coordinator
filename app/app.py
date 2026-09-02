import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    
import streamlit as st

st.set_page_config(
    page_title="AI Disaster Response Coordinator",
    page_icon="🚨",
    layout="wide"
)

st.title("🚨 AI Disaster Response Coordinator")

st.markdown("""
Welcome to the **AI Disaster Response Coordinator**.

Use the navigation menu on the left to access:

- 📊 Dashboard
- 🚨 Report Incident
- 📜 Incident History
- 🏥 Hospitals
- 🏠 Shelters
- 🙋 Volunteers
- 📈 Analytics
- ⚙ Settings
""")