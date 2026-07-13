def assess_incident(incident):

    if incident.people_affected >= 100:

        priority = "Critical"

    elif incident.people_affected >= 50:

        priority = "High"

    elif incident.people_affected >= 10:

        priority = "Medium"

    else:

        priority = "Low"

    return priority