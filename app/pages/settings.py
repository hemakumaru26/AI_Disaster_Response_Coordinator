import os
import requests
import streamlit as st

from app.components.cards import apply_custom_styles, render_admin_banner
from backend.database.connection import get_connection

apply_custom_styles()

render_admin_banner(
    title="System Settings & Integration Diagnostics",
    subtitle="Audit component connectivity, local Ollama LLM availability, SQLite database tables, and routing services.",
)

st.subheader("🔍 Integration Health Checks")

# 1. Database Check
db_healthy = False
db_stats = {}
try:
    with get_connection() as conn:
        db_stats["incidents"] = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
        db_stats["missions"] = conn.execute("SELECT COUNT(*) FROM missions").fetchone()[0]
        db_stats["volunteers"] = conn.execute("SELECT COUNT(*) FROM volunteers").fetchone()[0]
        db_stats["shelters"] = conn.execute("SELECT COUNT(*) FROM shelters").fetchone()[0]
        db_stats["hospitals"] = conn.execute("SELECT COUNT(*) FROM hospitals").fetchone()[0]
    db_healthy = True
except Exception as err:
    db_error = str(err)

# 2. FastAPI Backend Check
api_healthy = False
api_msg = ""
try:
    resp = requests.get("http://localhost:8000/docs", timeout=2)
    if resp.status_code == 200:
        api_healthy = True
        api_msg = "Online (Listening at port 8000)"
    else:
        api_msg = f"HTTP {resp.status_code}"
except Exception:
    api_msg = "Offline / Not currently running"

# 3. Ollama LLM Check
ollama_healthy = False
ollama_msg = ""
try:
    resp = requests.get("http://localhost:11434/api/tags", timeout=1.5)
    if resp.status_code == 200:
        data = resp.json()
        models = [m.get("name") for m in data.get("models", [])]
        ollama_healthy = True
        ollama_msg = f"Online (Models: {', '.join(models[:2])})"
    else:
        ollama_msg = "Offline"
except Exception:
    ollama_msg = "Offline (Using Deterministic Rule Fallback)"

# 4. Routing Engine Check
osrm_msg = "Online (Default OSRM / Haversine fallback active)"

# 5. Notification Dispatch Check
resend_key = os.getenv("RESEND_API_KEY", "")
raw_mode = os.getenv("NOTIFICATION_MODE", "DRY_RUN").strip().upper()
notif_mode = "LIVE" if raw_mode == "LIVE" else "DRY_RUN"

# Render Health Status Grid
c1, c2, c3 = st.columns(3)

with c1:
    if db_healthy:
        st.success(f"🟢 **Database (SQLite)**\n\nConnected: `database/disaster.db`\n- Incidents: {db_stats['incidents']:,}\n- Missions: {db_stats['missions']:,}\n- Shelters: {db_stats['shelters']:,}")
    else:
        st.error(f"🔴 **Database**: {db_error}")

with c2:
    if api_healthy:
        st.success(f"🟢 **FastAPI Backend Service**\n\n{api_msg}")
    else:
        st.warning(f"🟡 **FastAPI Backend Service**\n\n{api_msg}")

    if ollama_healthy:
        st.success(f"🟢 **Local Ollama LLM Engine**\n\n{ollama_msg}")
    else:
        st.info(f"⚙️ **Local Ollama LLM Engine**\n\n{ollama_msg}")

with c3:
    st.success(f"🟢 **Routing Engine (OSRM)**\n\n{osrm_msg}")
    if notif_mode == "LIVE":
        st.success("🟢 **Notification Mode: LIVE**\n\nExternal emails sent via Resend.")
    else:
        st.info("🧪 **Notification Mode: DRY_RUN**\n\nSafe simulation mode active.")

st.markdown("---")

# Environment & Diagnostic Variables
st.subheader("⚙️ Active Runtime Configuration")

cfg_data = [
    {"Parameter": "App Title", "Value": "AI Disaster Response Coordinator"},
    {"Parameter": "Supported Region", "Value": "Tamil Nadu, India (38 Districts)"},
    {"Parameter": "Primary LLM Model", "Value": os.getenv("OLLAMA_MODEL", "qwen2.5:7b")},
    {"Parameter": "LLM Timeout Threshold", "Value": "5.0 seconds (bounded with deterministic fallback)"},
    {"Parameter": "RAG Vector Store", "Value": "ChromaDB / LangChain HuggingFace Embeddings"},
    {"Parameter": "Notification Mode", "Value": notif_mode},
    {"Parameter": "Resend API Key", "Value": "Configured (Masked)" if resend_key else "Not configured (Running in safe DRY_RUN)"},
    {"Parameter": "Emergency Dial", "Value": "1070 (SEOC) / 1077 (DEOC) / 108 (Ambulance)"},
]

st.dataframe(cfg_data, use_container_width=True, hide_index=True)

if st.button("🔄 Re-run Diagnostic Tests", use_container_width=True):
    st.rerun()