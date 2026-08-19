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

from backend.services.maps_service import geocode_location

from agents.assessment.assessment_agent import (
    AssessmentAgent
)
from agents.shelter_finder_agent import ShelterFinderAgent

router = APIRouter()

assessment_agent = AssessmentAgent()
shelter_finder_agent = ShelterFinderAgent()


def get_shelter_recommendations(incident):
    """Return incident coordinates and ranked shelter recommendations safely."""
    try:
        coordinates = geocode_location(incident.location)
        if coordinates is None:
            return None, [], "Incident location could not be geocoded."

        shelters = shelter_finder_agent.find_nearest_shelters(
            victim_latitude=coordinates["latitude"],
            victim_longitude=coordinates["longitude"],
            required_capacity=incident.people_affected,
            limit=5,
        )
        return coordinates, shelters, None
    except Exception:
        # Map data is supplemental and must never block incident recording.
        return None, [], "Shelter map is unavailable for this location."


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

    incident_coordinates, nearest_shelters, shelter_map_message = (
        get_shelter_recommendations(incident)
    )

    return {
        "incident_id": incident_id,
        "assessment": {
            "priority": assessment["priority"],
            "severity_score": severity_score,
            "resources": assessment["resources"],
            "reason": assessment["reason"]
        },
        "incident_coordinates": incident_coordinates,
        "nearest_shelters": nearest_shelters,
        "shelter_map_message": shelter_map_message,
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
