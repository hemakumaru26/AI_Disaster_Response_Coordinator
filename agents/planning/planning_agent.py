"""Deterministic rescue-plan composition from existing agent outputs."""


class PlanningAgent:
    """Build explainable rescue plans without performing resource searches."""

    @staticmethod
    def _value(source, key, default=None):
        if isinstance(source, dict):
            return source.get(key, default)
        return getattr(source, key, default)

    def _validate_inputs(
        self, incident, assessment, hospitals, shelters, volunteer_allocation, rag_context
    ):
        incident_id = self._value(incident, "id", self._value(incident, "incident_id"))
        if not isinstance(incident_id, int) or incident_id < 1:
            raise ValueError("incident must provide a positive integer id.")
        if not isinstance(assessment, dict):
            raise ValueError("assessment must be a dictionary.")

        priority = assessment.get("priority")
        if not isinstance(priority, str) or not priority.strip():
            raise ValueError("assessment must contain a non-empty priority.")
        resources = assessment.get("resources", [])
        if not isinstance(resources, list) or not all(
            isinstance(resource, str) and resource.strip() for resource in resources
        ):
            raise ValueError("assessment resources must be a list of non-empty strings.")
        if not isinstance(hospitals, list) or not all(
            isinstance(hospital, dict) for hospital in hospitals
        ):
            raise ValueError("hospitals must be a list of dictionaries.")
        if not isinstance(shelters, list) or not all(
            isinstance(shelter, dict) for shelter in shelters
        ):
            raise ValueError("shelters must be a list of dictionaries.")
        if volunteer_allocation is not None and not isinstance(
            volunteer_allocation, dict
        ):
            raise ValueError("volunteer_allocation must be a dictionary or None.")
        if rag_context is not None and not isinstance(rag_context, dict):
            raise ValueError("rag_context must be a dictionary or None.")

        return incident_id, priority.strip(), [resource.strip() for resource in resources]

    @staticmethod
    def _available_shelter_capacity(shelters):
        capacities = [
            shelter["available_capacity"]
            for shelter in shelters
            if isinstance(shelter.get("available_capacity"), (int, float))
        ]
        return sum(capacities) if capacities else None

    @staticmethod
    def _volunteer_assignments(volunteer_allocation):
        if volunteer_allocation is None:
            return []
        assignments = volunteer_allocation.get("assignments", [])
        if not isinstance(assignments, list) or not all(
            isinstance(assignment, dict) for assignment in assignments
        ):
            raise ValueError("volunteer_allocation assignments must be a list.")
        return assignments

    def create_plan(
        self,
        incident,
        assessment,
        hospitals=None,
        shelters=None,
        volunteer_allocation=None,
        rag_context=None,
    ):
        """Create a structured plan from supplied outputs without inventing data."""
        hospitals = [] if hospitals is None else hospitals
        shelters = [] if shelters is None else shelters
        incident_id, priority, resources = self._validate_inputs(
            incident, assessment, hospitals, shelters, volunteer_allocation, rag_context
        )
        volunteer_plan = self._volunteer_assignments(volunteer_allocation)

        resource_gaps = []
        risk_notes = []
        people_affected = self._value(incident, "people_affected")
        available_capacity = self._available_shelter_capacity(shelters)

        if volunteer_allocation is not None:
            requested_count = volunteer_allocation.get("requested_count")
            assigned_count = volunteer_allocation.get("assigned_count")
            unmet_count = volunteer_allocation.get("unmet_count")
            if all(isinstance(value, int) and value >= 0 for value in (
                requested_count, assigned_count, unmet_count
            )) and unmet_count > 0:
                resource_gaps.append(
                    f"Volunteer shortfall: {unmet_count} of {requested_count} requested."
                )
            for skill in volunteer_allocation.get("unmet_skills", []):
                if isinstance(skill, str) and skill.strip():
                    resource_gaps.append(f"Unmet volunteer skill: {skill.strip()}.")

        if isinstance(people_affected, int) and people_affected > 0:
            if available_capacity is not None and available_capacity < people_affected:
                resource_gaps.append(
                    "Shelter capacity shortfall: "
                    f"{available_capacity} available for {people_affected} people."
                )
            elif not shelters:
                resource_gaps.append("No shelter options supplied for affected people.")

        medical_resources = {"ambulance", "medical team"}
        if not hospitals and any(
            resource.lower() in medical_resources for resource in resources
        ):
            resource_gaps.append("No hospital options supplied for medical support.")

        allocated_resource_types = set()
        if hospitals:
            allocated_resource_types.update(medical_resources)
        if shelters:
            allocated_resource_types.add("shelter")
        if volunteer_plan:
            allocated_resource_types.update({"rescue team", "relief team"})
        for resource in resources:
            if resource.lower() not in allocated_resource_types:
                resource_gaps.append(
                    f"No corresponding allocation data supplied for resource: {resource}."
                )

        assessment_reason = assessment.get("reason")
        if isinstance(assessment_reason, str) and assessment_reason.strip():
            risk_notes.append(assessment_reason.strip())
        if resource_gaps:
            risk_notes.append("Resolve identified resource gaps before activation.")

        response_steps = [
            f"Confirm incident {incident_id} and {priority} priority response.",
        ]
        if resources:
            response_steps.append(
                f"Prepare assessed resources: {', '.join(resources)}."
            )
        if hospitals:
            response_steps.append("Coordinate with the supplied hospital options.")
        if shelters:
            response_steps.append("Prepare the supplied shelter options for evacuation.")
        if volunteer_plan:
            response_steps.append("Brief and deploy assigned volunteers.")
        if resource_gaps:
            response_steps.append("Escalate unresolved resource gaps to the coordinator.")

        return {
            "incident_id": incident_id,
            "priority": priority,
            "objective": f"Coordinate a {priority} priority response for incident {incident_id}.",
            "required_resources": resources,
            "hospital_plan": list(hospitals),
            "shelter_plan": list(shelters),
            "volunteer_plan": volunteer_plan,
            "rag_context": rag_context,
            "response_steps": response_steps,
            "resource_gaps": resource_gaps,
            "risk_notes": risk_notes,
            "status": "planned",
        }
