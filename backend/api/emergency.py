from fastapi import APIRouter

from backend.schemas.incident_schema import IncidentSchema

from backend.models.incident_model import (
    save_incident,
    get_all_incidents,
    get_dashboard_stats
)

from backend.services.scoring_service import (
    calculate_severity
)

from agents.assessment.assessment_agent import (
    AssessmentAgent
)

router = APIRouter()

assessment_agent = AssessmentAgent()


@router.post("/report")
def report_incident(incident: IncidentSchema):
    """
    Analyze an emergency incident using AI,
    calculate severity score,
    and save everything into SQLite.
    """

    # AI Assessment
    assessment = assessment_agent.assess(incident)

    # Deterministic severity score
    severity_score = calculate_severity(incident)

    # Save into SQLite
    incident_id = save_incident(
        incident=incident,
        priority=assessment["priority"],
        severity_score=severity_score,
        resources=assessment["resources"]
    )

    return {
        "incident_id": incident_id,
        "assessment": {
            "priority": assessment["priority"],
            "severity_score": severity_score,
            "resources": assessment["resources"],
            "reason": assessment["reason"]
        }
    }


@router.get("/history")
def incident_history():
    """
    Return all incidents.
    """
    return get_all_incidents()


@router.get("/dashboard")
def dashboard():
    """
    Dashboard statistics.
    """
    return get_dashboard_stats()