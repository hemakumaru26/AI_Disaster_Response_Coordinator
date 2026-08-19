"""Find nearby shelters that can accommodate a reported incident."""

import math
import sqlite3
from pathlib import Path


class ShelterFinderAgent:
    """Ranks shelters by available capacity and distance from an incident."""

    DATABASE_PATH = (
        Path(__file__).resolve().parents[1] / "database" / "disaster.db"
    )

    def get_all_shelters(self):
        """Return the shelter fields used by the recommendation workflow."""
        with sqlite3.connect(self.DATABASE_PATH) as connection:
            cursor = connection.execute(
                """
                SELECT id, name, district, address, latitude, longitude,
                       capacity, occupancy, contact
                FROM shelters
                """
            )
            return cursor.fetchall()

    def get_shelter_by_id(self, shelter_id):
        """Return one shelter with its calculated available capacity, if found."""
        with sqlite3.connect(self.DATABASE_PATH) as connection:
            row = connection.execute(
                """
                SELECT id, name, district, address, latitude, longitude,
                       capacity, occupancy, contact
                FROM shelters
                WHERE id = ?
                """,
                (shelter_id,),
            ).fetchone()

        if row is None:
            return None

        return self._shelter_to_dict(row)

    def update_occupancy(self, shelter_id, people_count):
        """Add people to a shelter without exceeding its total capacity.

        Returns a dictionary that clearly states whether the update succeeded.
        """
        if people_count < 0:
            return {
                "success": False,
                "message": "people_count cannot be negative.",
            }

        with sqlite3.connect(self.DATABASE_PATH) as connection:
            cursor = connection.execute(
                """
                UPDATE shelters
                SET occupancy = occupancy + ?
                WHERE id = ?
                  AND occupancy + ? <= capacity
                """,
                (people_count, shelter_id, people_count),
            )

            if cursor.rowcount == 1:
                shelter_row = connection.execute(
                    """
                    SELECT id, name, district, address, latitude, longitude,
                           capacity, occupancy, contact
                    FROM shelters
                    WHERE id = ?
                    """,
                    (shelter_id,),
                ).fetchone()
                return {
                    "success": True,
                    "message": "Shelter occupancy updated successfully.",
                    "shelter": self._shelter_to_dict(shelter_row),
                }

            shelter_exists = connection.execute(
                "SELECT 1 FROM shelters WHERE id = ?", (shelter_id,)
            ).fetchone()

        if shelter_exists is None:
            return {"success": False, "message": "Shelter not found."}
        return {
            "success": False,
            "message": "Update would exceed the shelter's total capacity.",
        }

    @staticmethod
    def _shelter_to_dict(shelter):
        """Convert a shelter row into the public response format."""
        (
            shelter_id,
            name,
            district,
            address,
            latitude,
            longitude,
            capacity,
            occupancy,
            contact,
        ) = shelter
        return {
            "id": shelter_id,
            "name": name,
            "district": district,
            "address": address,
            "latitude": latitude,
            "longitude": longitude,
            "capacity": capacity,
            "occupancy": occupancy,
            "available_capacity": capacity - occupancy,
            "contact": contact,
        }

    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """Calculate the Haversine distance between two coordinates in km."""
        earth_radius_km = 6371.0
        latitude_delta = math.radians(lat2 - lat1)
        longitude_delta = math.radians(lon2 - lon1)

        a = (
            math.sin(latitude_delta / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(longitude_delta / 2) ** 2
        )
        angle = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(earth_radius_km * angle, 2)

    def find_nearest_shelters(
        self,
        victim_latitude,
        victim_longitude,
        required_capacity=1,
        limit=5,
    ):
        """Return suitable shelters ordered by a 50/50 suitability score.

        Distance contributes up to 50 points (nearer is better), and available
        capacity contributes up to 50 points (more space is better). Both
        values are normalized against the shelters eligible for this request.
        """
        if required_capacity < 1:
            raise ValueError("required_capacity must be at least 1.")
        if limit < 1:
            raise ValueError("limit must be at least 1.")

        shelters = self.get_all_shelters()
        suitable_shelters = []

        for shelter in shelters:
            (
                shelter_id,
                name,
                district,
                address,
                latitude,
                longitude,
                capacity,
                occupancy,
                contact,
            ) = shelter

            available_capacity = capacity - occupancy

            # Skip shelters that cannot accommodate the required group.
            if available_capacity < required_capacity:
                continue

            distance = self.calculate_distance(
                victim_latitude,
                victim_longitude,
                latitude,
                longitude,
            )
            shelter_data = self._shelter_to_dict(
                (
                    shelter_id,
                    name,
                    district,
                    address,
                    latitude,
                    longitude,
                    capacity,
                    occupancy,
                    contact,
                )
            )
            shelter_data["distance_km"] = distance
            suitable_shelters.append(shelter_data)

        if not suitable_shelters:
            return []

        maximum_distance = max(
            shelter["distance_km"] for shelter in suitable_shelters
        )
        maximum_available_capacity = max(
            shelter["available_capacity"] for shelter in suitable_shelters
        )

        for shelter in suitable_shelters:
            distance_score = (
                50
                if maximum_distance == 0
                else 50 * (1 - shelter["distance_km"] / maximum_distance)
            )
            capacity_score = 50 * (
                shelter["available_capacity"] / maximum_available_capacity
            )
            shelter["suitability_score"] = round(
                distance_score + capacity_score, 2
            )

        suitable_shelters.sort(
            key=lambda shelter: (
                -shelter["suitability_score"],
                shelter["distance_km"],
            )
        )
        return suitable_shelters[:limit]


if __name__ == "__main__":
    agent = ShelterFinderAgent()

    # Example disaster location: Chennai.
    nearest_shelters = agent.find_nearest_shelters(
        victim_latitude=13.0827,
        victim_longitude=80.2707,
        required_capacity=100,
        limit=5,
    )

    print("\nNEAREST SHELTERS")
    print("=" * 70)

    for shelter in nearest_shelters:
        print(f"\nName: {shelter['name']}")
        print(f"District: {shelter['district']}")
        print(f"Address: {shelter['address']}")
        print(f"Total Capacity: {shelter['capacity']}")
        print(f"Current Occupancy: {shelter['occupancy']}")
        print(f"Available Capacity: {shelter['available_capacity']}")
        print(f"Distance: {shelter['distance_km']} km")
        print(f"Suitability Score: {shelter['suitability_score']}")
        print(f"Contact: {shelter['contact']}")
