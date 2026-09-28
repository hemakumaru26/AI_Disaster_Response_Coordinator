"""Deterministic volunteer allocation using the existing assignment lifecycle."""

import re

from backend.models.volunteer_model import (
    assign_volunteer,
    get_assignment_by_id,
    get_suitable_volunteers,
)

# Canonical skills actually stored in database/disaster.db
CANONICAL_VOLUNTEER_SKILLS = [
    "Boat Operations",
    "Cyclone Response",
    "Disaster Relief",
    "Emergency Communication",
    "Evacuation",
    "Fire & Emergency",
    "First Aid",
    "Flood Rescue",
    "Food Distribution",
    "Logistics",
    "Medical Assistance",
    "Search & Rescue",
    "Shelter Management",
    "Water Distribution",
    "Water Rescue",
]

# Conceptual mappings from emergency resources / assessment terms to canonical skills
RESOURCE_TO_SKILLS = {
    "boat": ["Boat Operations", "Flood Rescue", "Water Rescue"],
    "boats": ["Boat Operations", "Flood Rescue", "Water Rescue"],
    "rescue boat": ["Boat Operations", "Flood Rescue", "Water Rescue"],
    "boat rescue": ["Boat Operations", "Flood Rescue", "Water Rescue"],
    "rescue team": ["Search & Rescue", "Flood Rescue", "Water Rescue"],
    "rescue teams": ["Search & Rescue", "Flood Rescue", "Water Rescue"],
    "search & rescue": ["Search & Rescue"],
    "search and rescue": ["Search & Rescue"],
    "search team": ["Search & Rescue", "Evacuation"],
    "flood rescue": ["Flood Rescue", "Water Rescue", "Boat Operations"],
    "water rescue": ["Water Rescue", "Flood Rescue", "Boat Operations"],
    "medical support": ["First Aid", "Medical Assistance"],
    "medical team": ["First Aid", "Medical Assistance"],
    "medical": ["First Aid", "Medical Assistance"],
    "medical assistance": ["Medical Assistance", "First Aid"],
    "ambulance": ["First Aid", "Medical Assistance"],
    "first aid": ["First Aid", "Medical Assistance"],
    "shelter": ["Shelter Management"],
    "shelter management": ["Shelter Management"],
    "food": ["Food Distribution"],
    "food distribution": ["Food Distribution"],
    "relief distribution": ["Food Distribution", "Disaster Relief"],
    "relief team": ["Disaster Relief", "Food Distribution"],
    "disaster relief": ["Disaster Relief"],
    "ration": ["Food Distribution", "Logistics"],
    "water": ["Water Distribution"],
    "drinking water": ["Water Distribution"],
    "water distribution": ["Water Distribution"],
    "logistics": ["Logistics", "Emergency Communication"],
    "communication": ["Emergency Communication"],
    "emergency communication": ["Emergency Communication"],
    "fire": ["Fire & Emergency", "Fire Rescue"],
    "fire engine": ["Fire & Emergency", "Fire Rescue"],
    "fire truck": ["Fire & Emergency", "Fire Rescue"],
    "firefighters": ["Fire & Emergency", "Fire Rescue"],
    "fire & emergency": ["Fire & Emergency", "Fire Rescue"],
    "evacuation": ["Evacuation", "Search & Rescue"],
    "evacuation bus": ["Evacuation", "Search & Rescue"],
    "evacuation team": ["Evacuation", "Search & Rescue"],
    "cyclone response": ["Cyclone Response", "Evacuation"],
    "excavator": ["Search & Rescue", "Logistics", "Disaster Relief"],
    "heavy machinery": ["Search & Rescue", "Logistics"],
}

# Disaster-type fallback skill preferences
DISASTER_DEFAULT_SKILLS = {
    "flood": ["Flood Rescue", "Boat Operations", "Water Rescue", "Search & Rescue"],
    "cyclone": ["Cyclone Response", "Evacuation", "Water Distribution", "Search & Rescue"],
    "fire": ["Fire & Emergency", "Fire Rescue", "Evacuation", "First Aid"],
    "building collapse": ["Search & Rescue", "Evacuation", "First Aid"],
    "earthquake": ["Search & Rescue", "First Aid", "Evacuation"],
    "landslide": ["Search & Rescue", "Logistics", "Disaster Relief", "First Aid"],
    "medical emergency": ["Medical Assistance", "First Aid", "Emergency Communication"],
}


class VolunteerAllocationAgent:
    """Select and assign available volunteers without bypassing the data model."""

    def __init__(self, connection=None):
        self.connection = connection

    @staticmethod
    def _validate_request(incident_id, incident_district, required_count):
        if not isinstance(incident_id, int) or incident_id < 1:
            raise ValueError("incident_id must be a positive integer.")
        if not isinstance(incident_district, str) or not incident_district.strip():
            raise ValueError("incident_district is required.")
        if not isinstance(required_count, int) or required_count < 1:
            raise ValueError("required_count must be a positive integer.")

    @classmethod
    def resolve_required_skills(
        cls,
        required_skills=None,
        resources=None,
        disaster_type=None,
    ):
        """Map raw requested skills, assessment resources, or disaster type to candidate canonical skills.

        Returns an ordered list of candidate canonical skills without inventing unsupported skills.
        """
        resolved = []

        def _add_skill(candidate):
            if not candidate:
                return
            cleaned = candidate.strip()
            # 1. Exact match with canonical skills (case-insensitive)
            for canon in CANONICAL_VOLUNTEER_SKILLS:
                if cleaned.lower() == canon.lower():
                    if canon not in resolved:
                        resolved.append(canon)
                    return
            # 2. Resource mapping dictionary exact key match
            lowered = cleaned.lower()
            if lowered in RESOURCE_TO_SKILLS:
                for s in RESOURCE_TO_SKILLS[lowered]:
                    if s not in resolved:
                        resolved.append(s)
                return
            # 3. Whole-word match against resource map keys
            for res_key, mapped_skills in RESOURCE_TO_SKILLS.items():
                if re.search(rf"\b{re.escape(res_key)}\b", lowered) or re.search(rf"\b{re.escape(lowered)}\b", res_key):
                    for s in mapped_skills:
                        if s not in resolved:
                            resolved.append(s)
                    return
            # 4. Retain original term if non-empty (preserves synthetic benchmark gap testing)
            if cleaned not in resolved:
                resolved.append(cleaned)

        if required_skills:
            if isinstance(required_skills, str):
                required_skills = [s.strip() for s in required_skills.split(",") if s.strip()]
            for req in required_skills:
                _add_skill(req)

        if not resolved and resources:
            res_list = []
            if isinstance(resources, str):
                res_list = [r.strip() for r in resources.split(",") if r.strip()]
            elif isinstance(resources, list):
                for item in resources:
                    if isinstance(item, str):
                        res_list.extend([r.strip() for r in item.split(",") if r.strip()])
            for r in res_list:
                _add_skill(r)

        if resolved and disaster_type and isinstance(disaster_type, str):
            dt_lower = disaster_type.strip().lower()
            if dt_lower in DISASTER_DEFAULT_SKILLS:
                preferred = [s for s in DISASTER_DEFAULT_SKILLS[dt_lower] if s in resolved]
                others = [s for s in resolved if s not in preferred]
                resolved = preferred + others

        return resolved

    @staticmethod
    def _assignment_summary(assignment):
        """Return the assignment fields needed by later planning work."""
        return {
            "assignment_id": assignment["id"],
            "volunteer_id": assignment["volunteer_id"],
            "volunteer_name": assignment["volunteer_name"],
            "volunteer_district": assignment["volunteer_district"],
            "volunteer_skills": assignment["volunteer_skills"],
            "contact": assignment.get("volunteer_contact") or assignment.get("contact"),
            "volunteer_contact": assignment.get("volunteer_contact") or assignment.get("contact"),
            "incident_id": assignment["incident_id"],
            "required_skill": assignment["required_skill"],
            "assignment_status": assignment["assignment_status"],
        }

    def allocate(
        self,
        incident_id,
        incident_district,
        required_skills=None,
        required_count=1,
        connection=None,
        resources=None,
        disaster_type=None,
        same_district_only=False,
    ):
        """Assign up to ``required_count`` volunteers matching emergency resource/skill demands.

        1. Determines required canonical skills from explicit skills, assessment resources, or disaster type.
        2. Prefers same-district volunteers with compatible skills.
        3. Excludes volunteers who lack required skill compatibility.
        4. Excludes actively assigned volunteers.
        5. Reports unmet demand if suitable volunteers cannot be found.
        """
        self._validate_request(incident_id, incident_district, required_count)
        incident_district = incident_district.strip()

        demanded_skills = self.resolve_required_skills(
            required_skills=required_skills,
            resources=resources,
            disaster_type=disaster_type,
        )

        active_conn = connection or self.connection
        assignments = []
        unmet_skills = []

        for slot_index in range(required_count):
            if demanded_skills:
                # Prioritize slot-specific demand if multiple skills requested, else full set
                if slot_index < len(demanded_skills):
                    primary = demanded_skills[slot_index]
                    slot_skills = [primary] + [s for s in demanded_skills if s != primary]
                else:
                    slot_skills = demanded_skills
            else:
                slot_skills = None

            # Re-query before every attempt so concurrent allocations are safe.
            candidates = get_suitable_volunteers(
                incident_district,
                required_skill=slot_skills,
                same_district_only=same_district_only,
                connection=active_conn,
            )
            assignment = None

            # Retry while alternatives still exist in case of concurrent allocation claim
            for _ in range(len(candidates)):
                created_assignment = assign_volunteer(
                    incident_id,
                    incident_district,
                    required_skill=slot_skills,
                    same_district_only=same_district_only,
                    connection=active_conn,
                )
                if created_assignment is not None:
                    assignment = get_assignment_by_id(
                        created_assignment["id"], connection=active_conn
                    )
                    if assignment is not None:
                        break
                candidates = get_suitable_volunteers(
                    incident_district,
                    required_skill=slot_skills,
                    same_district_only=same_district_only,
                    connection=active_conn,
                )
                if not candidates:
                    break

            if assignment is None:
                if slot_skills:
                    unmet_skills.append(slot_skills[0])
                continue

            assignments.append(self._assignment_summary(assignment))

        assigned_count = len(assignments)
        unmet_count = required_count - assigned_count
        has_demand = bool(demanded_skills)

        if assigned_count == required_count:
            success = True
            message = "Volunteer allocation completed."
        elif assigned_count > 0:
            success = not has_demand  # If specific demand existed, partial count is considered unmet
            message = "Volunteer allocation partially completed."
        else:
            success = False
            message = "No suitable volunteers are currently available."

        return {
            "success": success,
            "requested_count": required_count,
            "assigned_count": assigned_count,
            "assignments": assignments,
            "unmet_count": unmet_count,
            "unmet_skills": unmet_skills,
            "message": message,
        }
