import math
import sqlite3
import requests
from pathlib import Path


class HospitalAgent:
    """
    Hospital Agent

    1. Converts incident location into coordinates using Nominatim.
    2. Reads hospitals from SQLite.
    3. Calculates straight-line distance using the Haversine formula.
    4. Returns the nearest hospitals.
    """

    DB_PATH = Path(__file__).resolve().parents[2] / "database" / "disaster.db"
    GEOCODE_URL = "https://nominatim.openstreetmap.org/search"

    # ---------------------------------------------------------
    # Get Coordinates
    # ---------------------------------------------------------

    def get_coordinates(self, location: str):

        params = {
            "q": location,
            "format": "json",
            "limit": 1
        }

        headers = {
            "User-Agent": "AI-Disaster-Response-Coordinator"
        }

        try:
            response = requests.get(
                self.GEOCODE_URL,
                params=params,
                headers=headers,
                timeout=10
            )

            response.raise_for_status()

            data = response.json()

            if not data:
                return None

            return (
                float(data[0]["lat"]),
                float(data[0]["lon"])
            )

        except Exception:
            return None

    # ---------------------------------------------------------
    # Haversine Distance
    # ---------------------------------------------------------

    def haversine(self, lat1, lon1, lat2, lon2):
        """
        Calculate straight-line distance in kilometres.
        """

        R = 6371

        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(d_lat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(d_lon / 2) ** 2
        )

        c = 2 * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a)
        )

        return R * c

    # ---------------------------------------------------------
    # Nearby Hospitals
    # ---------------------------------------------------------

    def get_nearby_hospitals(self, location: str):

        incident_coordinates = self.get_coordinates(location)

        if incident_coordinates is None:
            return []

        incident_lat, incident_lon = incident_coordinates
        return self.get_nearby_hospitals_by_coordinates(
            incident_lat, incident_lon
        )

    def get_nearby_hospitals_by_coordinates(self, incident_lat, incident_lon):
        """Return the ten closest hospitals to known latitude/longitude values."""

        with sqlite3.connect(self.DB_PATH) as connection:
            rows = connection.execute("""
                SELECT
                    name,
                    district,
                    address,
                    latitude,
                    longitude,
                    phone,
                    hospital_type,
                    specialties
                FROM hospitals
            """).fetchall()

        hospitals = []

        for row in rows:

            try:

                hospital_lat = float(row[3])
                hospital_lon = float(row[4])

                distance = self.haversine(
                    incident_lat,
                    incident_lon,
                    hospital_lat,
                    hospital_lon
                )

                hospitals.append({

                    "name": row[0],
                    "district": row[1],
                    "address": row[2],
                    "latitude": hospital_lat,
                    "longitude": hospital_lon,
                    "phone": row[5],
                    "hospital_type": row[6],
                    "specialties": row[7],
                    "straight_distance_km": round(distance, 2)

                })

            except Exception:
                continue

        hospitals.sort(
            key=lambda hospital: hospital["straight_distance_km"]
        )

        return hospitals[:10]


if __name__ == "__main__":
    agent = HospitalAgent()
    hospitals = agent.get_nearby_hospitals_by_coordinates(13.0827, 80.2707)

    print("NEARBY HOSPITALS")
    print("=" * 70)
    for hospital in hospitals:
        print(
            f"{hospital['name']} | {hospital['district']} | "
            f"{hospital['straight_distance_km']} km"
        )
