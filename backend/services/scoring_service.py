def calculate_severity(incident):
    """
    Calculate a deterministic severity score (0–100)
    based on disaster type, people affected and keywords.
    """

    score = 0

    disaster = incident.disaster_type.lower()

    # Base score by disaster type
    if disaster == "earthquake":
        score += 35

    elif disaster == "cyclone":
        score += 30

    elif disaster == "flood":
        score += 25

    elif disaster == "landslide":
        score += 30

    elif disaster == "fire":
        score += 20

    # People affected
    people = incident.people_affected

    if people >= 100:
        score += 40

    elif people >= 50:
        score += 30

    elif people >= 20:
        score += 20

    elif people >= 5:
        score += 10

    else:
        score += 5

    description = incident.description.lower()

    keywords = {
        "dead": 20,
        "death": 20,
        "died": 20,
        "injured": 15,
        "bleeding": 15,
        "collapse": 20,
        "collapsed": 20,
        "trapped": 20,
        "medical": 15,
        "unconscious": 20,
        "spread": 10,
        "destroyed": 10,
    }

    for word, value in keywords.items():
        if word in description:
            score += value

    return min(score, 100)