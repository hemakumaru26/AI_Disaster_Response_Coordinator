from fastapi import FastAPI

from backend.api.emergency import router as emergency_router

app = FastAPI(
    title="AI Disaster Response Coordinator",
    version="1.0.0",
    description="Agentic AI Disaster Management System"
)

app.include_router(
    emergency_router,
    prefix="/emergency",
    tags=["Emergency"]
)


@app.get("/")
def root():
    return {
        "status": "running",
        "project": "AI Disaster Response Coordinator",
        "version": "1.0.0"
    }