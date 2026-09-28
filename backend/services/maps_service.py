import requests

# Free APIs
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"


HEADERS = {
    "User-Agent": "AI-Disaster-Response-Coordinator/1.0"
}


TN_DISTRICT_COORDINATES = {
    "ariyalur": {"latitude": 11.209, "longitude": 79.2046, "display_name": "Ariyalur, Tamil Nadu, India"},
    "chengalpattu": {"latitude": 12.7286, "longitude": 80.0397, "display_name": "Chengalpattu, Tamil Nadu, India"},
    "chennai": {"latitude": 13.0312, "longitude": 80.221, "display_name": "Chennai, Tamil Nadu, India"},
    "coimbatore": {"latitude": 11.0082, "longitude": 76.9746, "display_name": "Coimbatore, Tamil Nadu, India"},
    "cuddalore": {"latitude": 11.5666, "longitude": 79.5603, "display_name": "Cuddalore, Tamil Nadu, India"},
    "dharmapuri": {"latitude": 12.1252, "longitude": 78.2066, "display_name": "Dharmapuri, Tamil Nadu, India"},
    "dindigul": {"latitude": 10.3347, "longitude": 77.844, "display_name": "Dindigul, Tamil Nadu, India"},
    "erode": {"latitude": 11.3832, "longitude": 77.5673, "display_name": "Erode, Tamil Nadu, India"},
    "kallakurichi": {"latitude": 11.7736, "longitude": 78.9913, "display_name": "Kallakurichi, Tamil Nadu, India"},
    "kancheepuram": {"latitude": 12.8498, "longitude": 79.8717, "display_name": "Kancheepuram, Tamil Nadu, India"},
    "kanyakumari": {"latitude": 8.2118, "longitude": 77.3522, "display_name": "Kanyakumari, Tamil Nadu, India"},
    "karur": {"latitude": 10.9354, "longitude": 78.0965, "display_name": "Karur, Tamil Nadu, India"},
    "krishnagiri": {"latitude": 12.5077, "longitude": 78.1617, "display_name": "Krishnagiri, Tamil Nadu, India"},
    "madurai": {"latitude": 9.9517, "longitude": 78.0915, "display_name": "Madurai, Tamil Nadu, India"},
    "mayiladuthurai": {"latitude": 11.1424, "longitude": 79.6936, "display_name": "Mayiladuthurai, Tamil Nadu, India"},
    "nagapattinam": {"latitude": 10.6966, "longitude": 79.7855, "display_name": "Nagapattinam, Tamil Nadu, India"},
    "namakkal": {"latitude": 11.2803, "longitude": 78.0956, "display_name": "Namakkal, Tamil Nadu, India"},
    "perambalur": {"latitude": 11.2682, "longitude": 78.8402, "display_name": "Perambalur, Tamil Nadu, India"},
    "pudukkottai": {"latitude": 10.3437, "longitude": 78.927, "display_name": "Pudukkottai, Tamil Nadu, India"},
    "ramanathapuram": {"latitude": 9.3991, "longitude": 78.8109, "display_name": "Ramanathapuram, Tamil Nadu, India"},
    "ranipet": {"latitude": 12.932, "longitude": 79.417, "display_name": "Ranipet, Tamil Nadu, India"},
    "salem": {"latitude": 11.6509, "longitude": 78.089, "display_name": "Salem, Tamil Nadu, India"},
    "sivaganga": {"latitude": 9.9092, "longitude": 78.6294, "display_name": "Sivaganga, Tamil Nadu, India"},
    "tenkasi": {"latitude": 9.0278, "longitude": 77.3845, "display_name": "Tenkasi, Tamil Nadu, India"},
    "thanjavur": {"latitude": 10.7238, "longitude": 79.2052, "display_name": "Thanjavur, Tamil Nadu, India"},
    "the nilgiris": {"latitude": 11.424, "longitude": 76.696, "display_name": "The Nilgiris, Tamil Nadu, India"},
    "nilgiris": {"latitude": 11.424, "longitude": 76.696, "display_name": "The Nilgiris, Tamil Nadu, India"},
    "theni": {"latitude": 9.9251, "longitude": 77.4464, "display_name": "Theni, Tamil Nadu, India"},
    "thoothukudi": {"latitude": 8.8236, "longitude": 78.0565, "display_name": "Thoothukudi, Tamil Nadu, India"},
    "tuticorin": {"latitude": 8.8236, "longitude": 78.0565, "display_name": "Thoothukudi, Tamil Nadu, India"},
    "tiruchirappalli": {"latitude": 10.8464, "longitude": 78.6438, "display_name": "Tiruchirappalli, Tamil Nadu, India"},
    "trichy": {"latitude": 10.8464, "longitude": 78.6438, "display_name": "Tiruchirappalli, Tamil Nadu, India"},
    "tirunelveli": {"latitude": 8.6444, "longitude": 77.6341, "display_name": "Tirunelveli, Tamil Nadu, India"},
    "tirupathur": {"latitude": 12.611, "longitude": 78.623, "display_name": "Tirupathur, Tamil Nadu, India"},
    "tiruppur": {"latitude": 11.0055, "longitude": 77.3611, "display_name": "Tiruppur, Tamil Nadu, India"},
    "tiruvallur": {"latitude": 13.2308, "longitude": 79.9123, "display_name": "Tiruvallur, Tamil Nadu, India"},
    "tiruvannamalai": {"latitude": 12.4416, "longitude": 79.1654, "display_name": "Tiruvannamalai, Tamil Nadu, India"},
    "tiruvarur": {"latitude": 10.7455, "longitude": 79.5424, "display_name": "Tiruvarur, Tamil Nadu, India"},
    "thiruvarur": {"latitude": 10.7455, "longitude": 79.5424, "display_name": "Tiruvarur, Tamil Nadu, India"},
    "vellore": {"latitude": 12.8783, "longitude": 79.008, "display_name": "Vellore, Tamil Nadu, India"},
    "villupuram": {"latitude": 12.034, "longitude": 79.5712, "display_name": "Villupuram, Tamil Nadu, India"},
    "virudhunagar": {"latitude": 9.5337, "longitude": 77.8598, "display_name": "Virudhunagar, Tamil Nadu, India"},
}


def geocode_location(location: str):
    """
    Convert a location name into latitude and longitude.
    First checks known Tamil Nadu districts for instant, reliable local resolution.
    Falls back to Nominatim with bounded timeout for detailed street addresses.
    """
    if not location or not isinstance(location, str):
        return None

    clean_loc = location.strip().lower()
    for district, coords in TN_DISTRICT_COORDINATES.items():
        if district in clean_loc or clean_loc in district:
            return {
                "latitude": coords["latitude"],
                "longitude": coords["longitude"],
                "display_name": coords["display_name"]
            }

    try:
        response = requests.get(
            NOMINATIM_URL,
            params={
                "q": location,
                "format": "json",
                "limit": 1
            },
            headers=HEADERS,
            timeout=3
        )
        response.raise_for_status()
        data = response.json()
        if data:
            return {
                "latitude": float(data[0]["lat"]),
                "longitude": float(data[0]["lon"]),
                "display_name": data[0]["display_name"]
            }
    except Exception:
        pass

    return None


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