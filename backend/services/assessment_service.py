from backend.models.incident_model import save_incident


def analyze_incident(incident):
    """
    Analyze an incident, assign priority,
    save it into SQLite, and return the result.
    """

    priority = "LOW"

    disaster = incident["disaster_type"].lower()
    people = incident["people_affected"]

    if disaster in ["earthquake", "cyclone"]:
        priority = "CRITICAL"

    elif people >= 100:
        priority = "CRITICAL"

    elif people >= 50:
        priority = "HIGH"

    elif people >= 10:
        priority = "MEDIUM"

    incident["priority"] = priority
    incident["status"] = "received"

    # Save into SQLite database
    incident_id = save_incident(incident)

    return {
        "id": incident_id,
        "status": incident["status"],
        "priority": incident["priority"],
        "incident": incident
    }