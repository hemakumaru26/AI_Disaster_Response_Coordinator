from fastapi import APIRouter, Body, HTTPException
from types import SimpleNamespace

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
from backend.services.mission_workflow import MissionWorkflow
from agents.assessment.assessment_agent import AssessmentAgent

router = APIRouter()

assessment_agent = AssessmentAgent()
mission_workflow = MissionWorkflow()


def get_incident_coordinates(incident):
    """Geocode the incident for workflow routing and supplemental map rendering."""
    try:
        coordinates = geocode_location(incident.location)
        if coordinates is None:
            return None, "Incident location could not be geocoded."
        return coordinates, None
    except Exception:
        # Map data is supplemental and must never block incident recording.
        return None, "Shelter map is unavailable for this location."


def _workflow_response(workflow_result):
    """Select the JSON-safe workflow data needed by the API client."""
    mission = workflow_result.get("mission") or {}
    return {
        "mission_id": workflow_result.get("mission_id") or mission.get("id"),
        "status": workflow_result.get("status") or mission.get("status"),
        "assessment": workflow_result.get("assessment"),
        "rag_context": workflow_result.get("rag_context"),
        "hospitals": workflow_result.get("hospitals", []),
        "shelters": workflow_result.get("shelters", []),
        "volunteer_allocation": workflow_result.get("volunteer_allocation"),
        "rescue_plan": workflow_result.get("rescue_plan"),
        "approval_status": workflow_result.get("approval_status") or mission.get("approval_status"),
        "mission": mission or None,
        "error": workflow_result.get("error"),
    }


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

    incident_coordinates, shelter_map_message = get_incident_coordinates(incident)
    workflow_incident = SimpleNamespace(
        id=incident_id,
        reporter_name=incident.reporter_name,
        phone=incident.phone,
        disaster_type=incident.disaster_type,
        location=incident.location,
        people_affected=incident.people_affected,
        description=incident.description,
    )
    workflow_state = {
        "incident": workflow_incident,
        "incident_district": incident.location,
        "assessment": assessment,
    }
    if incident_coordinates is not None:
        workflow_state["incident_coordinates"] = (
            incident_coordinates["latitude"],
            incident_coordinates["longitude"],
        )

    try:
        workflow_result = mission_workflow.run(workflow_state)
    except Exception as error:
        workflow_result = {
            "status": "failed",
            "error": f"workflow execution failed: {error}",
        }
    workflow = _workflow_response(workflow_result)
    return {
        "incident_id": incident_id,
        "assessment": {
            "priority": assessment["priority"],
            "severity_score": severity_score,
            "resources": assessment["resources"],
            "reason": assessment["reason"]
        },
        "incident_coordinates": incident_coordinates,
        "nearest_shelters": workflow["shelters"],
        "shelter_map_message": shelter_map_message,
        "mission_id": workflow["mission_id"],
        "workflow_status": workflow["status"],
        "workflow": workflow,
    }


@router.get("/history")
def incident_history():
    """
    Return all incidents.
    """
    return get_all_incidents()


@router.post("/missions/{mission_id}/approve")
def approve_mission(mission_id: int):
    """Apply the explicit human approval transition for one pending mission."""
    try:
        result = mission_workflow.approve_mission(mission_id)
    except (ValueError, RuntimeError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    mission = result.get("mission") or result
    communications = result.get("communications")
    notification_dispatch = result.get("notification_dispatch") or {}
    dispatch_mode = notification_dispatch.get("dispatch_mode", "DRY_RUN")
    sent_count = notification_dispatch.get("sent", 0)
    dispatched = bool(dispatch_mode == "LIVE" and sent_count > 0)

    if dispatch_mode == "DRY_RUN":
        message = (
            "Mission approved and activated. Emergency notifications simulated in "
            "DRY-RUN mode (no external messages sent)."
        )
    elif dispatched:
        message = (
            f"Mission approved and activated. Email notification via Resend "
            f"({sent_count} live email requests submitted)."
        )
    else:
        message = (
            "Mission approved and activated. Emergency communications processed "
            "(no live external emails dispatched)."
        )

    return {
        "mission_id": mission["mission_id"],
        "status": mission["status"],
        "approval_status": mission["approval_status"],
        "mission": mission,
        "communications": communications,
        "communication_status": communications.get("communication_status") if isinstance(communications, dict) else None,
        "dispatch_mode": dispatch_mode,
        "dispatched": dispatched,
        "notification_dispatch": notification_dispatch,
        "message": message,
    }


@router.post("/missions/{mission_id}/reject")
def reject_mission(mission_id: int, payload: dict | None = Body(None)):
    """Apply the explicit human rejection transition for one pending mission."""
    feedback = (payload or {}).get("feedback") if isinstance(payload, dict) else None
    try:
        result = mission_workflow.reject_mission(mission_id, feedback=feedback)
    except (ValueError, RuntimeError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    mission = result.get("mission") or result
    response_data = {
        "mission_id": mission["mission_id"],
        "status": mission["status"],
        "approval_status": mission["approval_status"],
        "released_volunteers": result.get("released_volunteers", 0),
        "mission": mission,
    }
    if result.get("feedback"):
        response_data["feedback"] = result["feedback"]
    return response_data


@router.post("/missions/{mission_id}/replan")
def replan_mission(mission_id: int, payload: dict | None = Body(None)):
    """Reflect on identified gaps and feedback to produce a revised rescue plan."""
    feedback = (payload or {}).get("feedback") if isinstance(payload, dict) else None
    try:
        result = mission_workflow.replan_mission(mission_id, feedback=feedback)
    except (ValueError, RuntimeError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    mission = result.get("mission") or result
    return {
        "mission_id": mission["mission_id"],
        "status": mission["status"],
        "approval_status": mission["approval_status"],
        "reflection": result.get("reflection"),
        "mission": mission,
    }


@router.post("/missions/{mission_id}/complete")
def complete_mission(mission_id: int):
    """Mark an active mission as completed and release assigned volunteers."""
    try:
        result = mission_workflow.complete_mission(mission_id)
    except (ValueError, RuntimeError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    mission = result.get("mission") or result
    return {
        "mission_id": mission["mission_id"],
        "status": mission["status"],
        "approval_status": mission["approval_status"],
        "completed_volunteers": result.get("completed_volunteers", 0),
        "released_shelter": result.get("released_shelter"),
        "mission": mission,
    }


@router.get("/dashboard")
def dashboard():
    """
    Dashboard statistics.
    """
    return get_dashboard_stats()
