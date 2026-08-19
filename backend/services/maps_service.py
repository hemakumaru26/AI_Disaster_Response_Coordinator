import requests

# Free APIs
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"


HEADERS = {
    "User-Agent": "AI-Disaster-Response-Coordinator/1.0"
}


def geocode_location(location: str):
    """
    Convert a location name into latitude and longitude.
    """

    response = requests.get(
        NOMINATIM_URL,
        params={
            "q": location,
            "format": "json",
            "limit": 1
        },
        headers=HEADERS,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    if not data:
        return None

    return {
        "latitude": float(data[0]["lat"]),
        "longitude": float(data[0]["lon"]),
        "display_name": data[0]["display_name"]
    }


def find_nearby_hospitals(latitude, longitude, radius=5000):
    """
    Search nearby hospitals using Overpass API.
    """

    query = f"""
    [out:json];
    (
      node["amenity"="hospital"](around:{radius},{latitude},{longitude});
      way["amenity"="hospital"](around:{radius},{latitude},{longitude});
      relation["amenity"="hospital"](around:{radius},{latitude},{longitude});
    );
    out center;
    """

    response = requests.post(
        OVERPASS_URL,
        data=query,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    hospitals = []

    for element in data["elements"]:

        hospitals.append({
            "name": element.get("tags", {}).get(
                "name",
                "Unknown Hospital"
            ),
            "latitude": element.get(
                "lat",
                element.get("center", {}).get("lat")
            ),
            "longitude": element.get(
                "lon",
                element.get("center", {}).get("lon")
            )
        })

    return hospitals


def find_nearby_shelters(latitude, longitude, radius=5000):
    """
    Search nearby shelters.
    """

    query = f"""
    [out:json];
    (
      node["amenity"="shelter"](around:{radius},{latitude},{longitude});
      way["amenity"="shelter"](around:{radius},{latitude},{longitude});
      relation["amenity"="shelter"](around:{radius},{latitude},{longitude});
    );
    out center;
    """

    response = requests.post(
        OVERPASS_URL,
        data=query,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    shelters = []

    for element in data["elements"]:

        shelters.append({
            "name": element.get("tags", {}).get(
                "name",
                "Unnamed Shelter"
            ),
            "latitude": element.get(
                "lat",
                element.get("center", {}).get("lat")
            ),
            "longitude": element.get(
                "lon",
                element.get("center", {}).get("lon")
            )
        })

    return shelters


def calculate_route(
    start_lat,
    start_lon,
    end_lat,
    end_lon
):
    """
    Calculate ETA and distance using OSRM.
    """

    url = (
        f"{OSRM_URL}/"
        f"{start_lon},{start_lat};"
        f"{end_lon},{end_lat}"
    )

    response = requests.get(
        url,
        params={
            "overview": "false"
        },
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if not data["routes"]:
        return None

    route = data["routes"][0]

    return {
        "distance_km": round(route["distance"] / 1000, 2),
        "duration_min": round(route["duration"] / 60, 1)
    }