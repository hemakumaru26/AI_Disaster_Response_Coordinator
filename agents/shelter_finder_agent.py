"""Find nearby shelters that can accommodate a reported incident."""

import math
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class ShelterFinderAgent:
    """Ranks shelters by available capacity and distance from an incident."""

    DATABASE_PATH = (
        Path(__file__).resolve().parents[1] / "database" / "disaster.db"
    )

    def __init__(self, database_path=None, connection=None):
        self.database_path = database_path or self.DATABASE_PATH
        self.connection = connection

    @contextmanager
    def _connection(self, connection=None):
        """Use an explicit or instance connection when supplied, else open database_path."""
        active = connection if connection is not None else self.connection
        if active is not None:
            yield active
        else:
            from backend.database.connection import DATABASE_PATH as PROJECT_DATABASE_PATH
            target_path = (
                self.database_path
                if self.database_path != self.DATABASE_PATH
                else PROJECT_DATABASE_PATH
            )
            with sqlite3.connect(target_path) as conn:
                yield conn

    def get_all_shelters(self, connection=None):
        """Return the shelter fields used by the recommendation workflow."""
        with self._connection(connection) as conn:
            cursor = conn.execute(
                """
                SELECT id, name, district, address, latitude, longitude,
                       capacity, occupancy, contact
                FROM shelters
                """
            )
            return cursor.fetchall()

    def get_shelter_by_id(self, shelter_id, connection=None):
        """Return one shelter with its calculated available capacity, if found."""
        with self._connection(connection) as conn:
            row = conn.execute(
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

    def update_occupancy(self, shelter_id, people_count, connection=None):
        """Add people to a shelter without exceeding its total capacity.

        Returns a dictionary that clearly states whether the update succeeded.
        """
        if people_count < 0:
            return {
                "success": False,
                "message": "people_count cannot be negative.",
            }

        with self._connection(connection) as conn:
            cursor = conn.execute(
                """
                UPDATE shelters
                SET occupancy = occupancy + ?
                WHERE id = ?
                  AND occupancy + ? <= capacity
                """,
                (people_count, shelter_id, people_count),
            )

            if cursor.rowcount == 1:
                conn.commit()
                shelter_row = conn.execute(
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

            shelter_exists = conn.execute(
                "SELECT 1 FROM shelters WHERE id = ?", (shelter_id,)
            ).fetchone()

        if shelter_exists is None:
            return {"success": False, "message": "Shelter not found."}
        return {
            "success": False,
            "message": "Update would exceed the shelter's total capacity.",
        }

    def release_occupancy(self, shelter_id, people_count, connection=None):
        """Release people from a shelter without dropping below zero.

        Returns a dictionary that clearly states whether the update succeeded.
        """
        if people_count < 0:
            return {
                "success": False,
                "message": "people_count cannot be negative.",
            }

        with self._connection(connection) as conn:
            cursor = conn.execute(
                """
                UPDATE shelters
                SET occupancy = MAX(0, occupancy - ?)
                WHERE id = ?
                """,
                (people_count, shelter_id),
            )

            if cursor.rowcount == 1:
                conn.commit()
                shelter_row = conn.execute(
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
                    "message": "Shelter occupancy released successfully.",
                    "shelter": self._shelter_to_dict(shelter_row),
                }

            shelter_exists = conn.execute(
                "SELECT 1 FROM shelters WHERE id = ?", (shelter_id,)
            ).fetchone()

        if shelter_exists is None:
            return {"success": False, "message": "Shelter not found."}
        return {
            "success": False,
            "message": "Failed to release shelter occupancy.",
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

    @staticmethod
    def _is_district_match(shelter_district, incident_district):
        """Robust case-insensitive match between shelter district and incident location."""
        if not shelter_district or not incident_district:
            return False
        s_d = str(shelter_district).strip().lower()
        inc = str(incident_district).strip().lower()
        if s_d == inc:
            return True
        # Check if shelter district is in comma-separated parts
        parts = [p.strip() for p in inc.split(",") if p.strip()]
        if s_d in parts:
            return True
        # Check word boundaries
        words = set(re.findall(r"\b[a-z]+\b", inc))
        return s_d in words

    def find_nearest_shelters(
        self,
        victim_latitude,
        victim_longitude,
        required_capacity=1,
        limit=5,
        incident_district=None,
        connection=None,
    ):
        """Return suitable shelters ordered by capacity eligibility, district preference, and distance.

        1. Only considers shelters with available_capacity >= required_capacity.
        2. If suitable shelters exist in the same incident district, prioritizes them.
        3. Within the priority group, ranks primarily by geographic distance ascending (nearest first).
        4. Uses available capacity and total capacity as secondary tie-breakers.
        5. If no shelter in the incident district meets capacity, falls back to nearest outside shelters.
        """
        if required_capacity < 1:
            raise ValueError("required_capacity must be at least 1.")
        if limit < 1:
            raise ValueError("limit must be at least 1.")

        shelters = self.get_all_shelters(connection=connection)
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

            available_capacity = capacity - (occupancy or 0)

            # Step 1: Skip shelters that cannot accommodate the required group.
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
                    occupancy or 0,
                    contact,
                )
            )
            shelter_data["distance_km"] = distance
            shelter_data["is_same_district"] = self._is_district_match(
                district, incident_district
            )
            suitable_shelters.append(shelter_data)

        if not suitable_shelters:
            return []

        # Step 2: Check if any suitable candidates exist in the same incident district.
        has_same_district_candidates = any(
            s["is_same_district"] for s in suitable_shelters
        )

        # Step 3 & 4: Sort by district priority (0 for same district if present, else 1),
        # distance ascending, and capacity descending as tie-breaker.
        suitable_shelters.sort(
            key=lambda s: (
                0 if (has_same_district_candidates and s["is_same_district"]) else 1,
                s["distance_km"],
                -s["available_capacity"],
                -s["capacity"],
                s["id"],
            )
        )

        # Calculate suitability score that strictly aligns with the ranking
        for s in suitable_shelters:
            if s.get("is_same_district"):
                base = 90.0
                dist_penalty = min(25.0, s["distance_km"] * 0.4)
                cap_bonus = min(1.5, (s["available_capacity"] / 3000.0) * 1.5)
                s["suitability_score"] = round(base - dist_penalty + cap_bonus + 8.5, 2)
            else:
                base = 65.0
                dist_penalty = min(35.0, s["distance_km"] * 0.25)
                cap_bonus = min(1.5, (s["available_capacity"] / 3000.0) * 1.5)
                s["suitability_score"] = round(base - dist_penalty + cap_bonus, 2)

        # Ensure suitability_score is strictly non-increasing across the ranked order
        for i in range(1, len(suitable_shelters)):
            if suitable_shelters[i]["suitability_score"] >= suitable_shelters[i - 1]["suitability_score"]:
                suitable_shelters[i]["suitability_score"] = round(
                    max(1.0, suitable_shelters[i - 1]["suitability_score"] - 0.1), 2
                )

        # Remove internal helper attribute and return top limit
        for s in suitable_shelters:
            s.pop("is_same_district", None)

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
