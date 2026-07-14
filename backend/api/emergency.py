from fastapi import APIRouter

from backend.schemas.incident_schema import IncidentSchema
from backend.services.assessment_service import analyze_incident
from backend.models.incident_model import (
    get_all_incidents,
    get_dashboard_stats
)

router = APIRouter()


@router.post("/report")
def report_incident(incident: IncidentSchema):

    result = analyze_incident(
        incident.model_dump()
    )

    return result


@router.get("/history")
def incident_history():
    return get_all_incidents()


@router.get("/dashboard")
def dashboard():
    return get_dashboard_stats()