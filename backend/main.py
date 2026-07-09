from fastapi import FastAPI

app = FastAPI(
    title="AI Disaster Response Coordinator",
    description="Multi-Agent AI Disaster Response System",
    version="1.0.0"
)

@app.get("/")
def home():
    return {
        "status": "running",
        "project": "AI Disaster Response Coordinator",
        "version": "1.0.0"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }