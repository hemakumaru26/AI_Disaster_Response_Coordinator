from fastapi import APIRouter

from backend.schemas.incident_schema import IncidentSchema
from backend.services.assessment_service import assess_incident

router = APIRouter()


@router.post("/report")
def report_incident(incident: IncidentSchema):

    priority = assess_incident(incident)

    return {
        "status": "received",
        "priority": priority,
        "incident": incident
    }