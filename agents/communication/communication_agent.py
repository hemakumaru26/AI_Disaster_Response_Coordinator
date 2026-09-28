"""Deterministic emergency communication agent for disaster response coordination."""

from typing import Any, Dict, List, Optional, Union


class CommunicationAgent:
    """Prepares structured emergency communications without sending external messages.

    Generates actionable notification payloads for:
    - Responders (Mission activation directives)
    - Hospitals (Medical preparedness and casualty influx alerts)
    - Shelters (Evacuee reception and capacity advisories)
    - Volunteers (Specialized deployment instructions)
    - Incident Reporter (Acknowledgment and community safety guidance)
    """

    COMMUNICATION_STATUS = "prepared"

    @staticmethod
    def _value(source: Any, key: str, default: Any = None) -> Any:
        """Safely retrieve a value from a dictionary or an object attribute."""
        if source is None:
            return default
        if isinstance(source, dict):
            return source.get(key, default)
        return getattr(source, key, default)

    @staticmethod
    def _clean_text(value: Any, default: str = "") -> str:
        """Return stripped string or default if empty/invalid."""
        if isinstance(value, str) and value.strip():
            return value.strip()
        return default

    def _extract_incident_metadata(self, incident: Any) -> Dict[str, Any]:
        """Normalize incident information from various input formats."""
        incident_id = self._value(incident, "id", self._value(incident, "incident_id"))
        reporter_name = self._clean_text(
            self._value(incident, "reporter_name", self._value(incident, "reporter")),
            default="Emergency Reporter",
        )
        phone = self._clean_text(
            self._value(incident, "phone", self._value(incident, "contact")),
            default="",
        )
        disaster_type = self._clean_text(
            self._value(incident, "disaster_type", self._value(incident, "disaster")),
            default="Disaster Incident",
        )
        location = self._clean_text(
            self._value(incident, "location"),
            default="Unspecified Location",
        )
        people_affected = self._value(incident, "people_affected")
        if not isinstance(people_affected, int) or people_affected < 0:
            people_affected = "Unspecified count"

        description = self._clean_text(
            self._value(incident, "description"),
            default="No specific incident description provided.",
        )

        return {
            "incident_id": incident_id,
            "reporter_name": reporter_name,
            "phone": phone or None,
            "disaster_type": disaster_type,
            "location": location,
            "people_affected": people_affected,
            "description": description,
        }

    def prepare_responder_message(
        self,
        incident_meta: Dict[str, Any],
        priority: str,
        reason: str,
        resources: List[str],
        rescue_plan: Optional[Dict[str, Any]],
        mission_id: Optional[int],
    ) -> Dict[str, Any]:
        """Generate a mission activation dispatch notification for primary responders."""
        incident_id_str = f"#{incident_meta['incident_id']}" if incident_meta["incident_id"] else "UNREGISTERED"
        mission_id_str = f"#{mission_id}" if mission_id else "PENDING"
        subject = f"[{priority}] MISSION ACTIVATION {mission_id_str}: {incident_meta['disaster_type']} at {incident_meta['location']}"

        resource_str = ", ".join(resources) if resources else "Standard emergency response deployment"
        response_steps = self._value(rescue_plan, "response_steps", [])
        steps_text = ""
        if isinstance(response_steps, list) and response_steps:
            numbered_steps = [f"  {idx + 1}. {step}" for idx, step in enumerate(response_steps)]
            steps_text = "\nAction Directives:\n" + "\n".join(numbered_steps)

        resource_gaps = self._value(rescue_plan, "resource_gaps", [])
        gaps_text = ""
        if isinstance(resource_gaps, list) and resource_gaps:
            gaps_text = f"\nResource Shortfalls / Attention Required: {'; '.join(resource_gaps)}"

        body = (
            f"EMERGENCY DISPATCH ALERT - MISSION {mission_id_str}\n"
            f"Incident Reference: {incident_id_str}\n"
            f"Disaster Type: {incident_meta['disaster_type']}\n"
            f"Location: {incident_meta['location']}\n"
            f"Priority Level: {priority}\n"
            f"Estimated People Affected: {incident_meta['people_affected']}\n"
            f"Required Resources: {resource_str}\n"
            f"Situation Summary: {incident_meta['description']}\n"
            f"Operational Context: {reason}"
            f"{steps_text}"
            f"{gaps_text}\n"
            f"Status: Authorized for deployment upon human approval."
        )

        return {
            "mission_id": mission_id,
            "communication_status": self.COMMUNICATION_STATUS,
            "target": "responders",
            "recipient": "Emergency Response Command / Incident Dispatch",
            "contact": "Central Dispatch Channel",
            "channel": "radio",
            "subject": subject,
            "title": subject,
            "message": body,
            "priority": priority,
            "reason": reason,
            "context": f"Mission activation for {incident_meta['disaster_type']} at {incident_meta['location']}",
        }

    def prepare_hospital_messages(
        self,
        hospitals: Optional[List[Dict[str, Any]]],
        incident_meta: Dict[str, Any],
        priority: str,
        mission_id: Optional[int],
    ) -> List[Dict[str, Any]]:
        """Generate medical preparedness and influx alerts for selected hospitals."""
        messages: List[Dict[str, Any]] = []
        if not hospitals or not isinstance(hospitals, list):
            return messages

        for hospital in hospitals:
            if not isinstance(hospital, dict):
                continue

            hospital_name = self._clean_text(hospital.get("name"), default="Emergency Hospital Facility")
            phone = self._clean_text(hospital.get("phone"), default="")
            address = self._clean_text(hospital.get("address"), default=hospital.get("district", "Area District"))
            distance = hospital.get("straight_distance_km")
            distance_str = f"{distance} km" if distance is not None else "Proximity not calculated"
            specialties = self._clean_text(hospital.get("specialties"), default="General Emergency")

            subject = f"[{priority}] MEDICAL ADVISORY: Potential Casualty Influx - {incident_meta['disaster_type']}"
            body = (
                f"MEDICAL FACILITY ALERT\n"
                f"To: {hospital_name}\n"
                f"Location: {address}\n"
                f"Distance from Incident Zone: {distance_str}\n"
                f"Specialties: {specialties}\n\n"
                f"Incident Context: {incident_meta['disaster_type']} reported at {incident_meta['location']}.\n"
                f"Estimated People Affected: {incident_meta['people_affected']}.\n"
                f"Triage Priority: {priority}.\n\n"
                f"Action Requested:\n"
                f"- Place emergency department and trauma triage on standby.\n"
                f"- Prepare acute care beds and medical supplies for influx.\n"
                f"- Acknowledge receipt via central emergency communications."
            )

            messages.append(
                {
                    "mission_id": mission_id,
                    "communication_status": self.COMMUNICATION_STATUS,
                    "target": "hospital",
                    "recipient": hospital_name,
                    "contact": phone or None,
                    "channel": "phone" if phone else "radio",
                    "subject": subject,
                    "title": subject,
                    "message": body,
                    "priority": priority,
                    "reason": f"Proximity medical readiness alert ({distance_str}) for {hospital_name}.",
                    "context": f"Hospital preparation for casualty influx from incident in {incident_meta['location']}.",
                }
            )

        return messages

    def prepare_shelter_messages(
        self,
        shelters: Optional[List[Dict[str, Any]]],
        incident_meta: Dict[str, Any],
        priority: str,
        mission_id: Optional[int],
    ) -> List[Dict[str, Any]]:
        """Generate evacuee intake and capacity preparation advisories for selected shelters."""
        messages: List[Dict[str, Any]] = []
        if not shelters or not isinstance(shelters, list):
            return messages

        for shelter in shelters:
            if not isinstance(shelter, dict):
                continue

            shelter_name = self._clean_text(shelter.get("name"), default="Designated Relief Shelter")
            contact = self._clean_text(shelter.get("contact"), default="")
            address = self._clean_text(shelter.get("address"), default=shelter.get("district", "Area District"))
            distance = shelter.get("distance_km")
            distance_str = f"{distance} km" if distance is not None else "Proximity not calculated"
            capacity = shelter.get("capacity", "N/A")
            available = shelter.get("available_capacity", "N/A")

            subject = f"[{priority}] SHELTER ADVISORY: Evacuee Intake Preparation - {incident_meta['disaster_type']}"
            body = (
                f"SHELTER INTAKE NOTICE\n"
                f"To: {shelter_name}\n"
                f"Location: {address}\n"
                f"Distance: {distance_str}\n"
                f"Registered Capacity: {capacity} | Available Space: {available}\n\n"
                f"Incident Context: Evacuation coordination underway for {incident_meta['disaster_type']} at {incident_meta['location']}.\n"
                f"Estimated People Displaced: {incident_meta['people_affected']}.\n\n"
                f"Action Requested:\n"
                f"- Prepare facility for immediate evacuee reception and registration.\n"
                f"- Verify clean water, food ration packs, and sanitation facilities.\n"
                f"- Coordinate reception with deployed emergency personnel."
            )

            messages.append(
                {
                    "mission_id": mission_id,
                    "communication_status": self.COMMUNICATION_STATUS,
                    "target": "shelter",
                    "recipient": shelter_name,
                    "contact": contact or None,
                    "channel": "sms" if contact else "phone",
                    "subject": subject,
                    "title": subject,
                    "message": body,
                    "priority": priority,
                    "reason": f"Evacuation intake coordination for {shelter_name} ({distance_str}).",
                    "context": f"Shelter readiness for {incident_meta['people_affected']} displaced individuals.",
                }
            )

        return messages

    def prepare_volunteer_messages(
        self,
        volunteer_allocation: Optional[Dict[str, Any]],
        incident_meta: Dict[str, Any],
        priority: str,
        mission_id: Optional[int],
    ) -> List[Dict[str, Any]]:
        """Generate deployment instructions for assigned volunteer personnel."""
        messages: List[Dict[str, Any]] = []
        if not volunteer_allocation or not isinstance(volunteer_allocation, dict):
            return messages

        assignments = volunteer_allocation.get("assignments")
        if not assignments or not isinstance(assignments, list):
            return messages

        for assignment in assignments:
            if not isinstance(assignment, dict):
                continue

            volunteer_name = self._clean_text(
                assignment.get("volunteer_name"), default="Volunteer Responder"
            )
            contact = self._clean_text(
                assignment.get("contact", assignment.get("volunteer_contact", assignment.get("phone"))),
                default="",
            )
            required_skill = self._clean_text(
                assignment.get("required_skill", assignment.get("volunteer_skills")),
                default="General Relief Support",
            )
            assignment_id = assignment.get("assignment_id", "N/A")

            subject = f"[{priority}] VOLUNTEER DEPLOYMENT: Mission #{mission_id or 'N/A'} - {incident_meta['disaster_type']}"
            body = (
                f"VOLUNTEER MISSION DIRECTIVE\n"
                f"Responder: {volunteer_name} (Assignment #{assignment_id})\n"
                f"Incident: {incident_meta['disaster_type']} at {incident_meta['location']}\n"
                f"Priority: {priority}\n"
                f"Assigned Function / Skill: {required_skill}\n\n"
                f"Instructions:\n"
                f"1. Proceed to the designated staging area for {incident_meta['location']}.\n"
                f"2. Check in with the on-site Incident Commander.\n"
                f"3. Maintain required safety gear and follow responder safety protocols.\n"
                f"4. Await operational briefing before entering active zones."
            )

            messages.append(
                {
                    "mission_id": mission_id,
                    "communication_status": self.COMMUNICATION_STATUS,
                    "target": "volunteers",
                    "recipient": volunteer_name,
                    "contact": contact or None,
                    "channel": "sms",
                    "subject": subject,
                    "title": subject,
                    "message": body,
                    "priority": priority,
                    "reason": f"Deployment directive for volunteer {volunteer_name} ({required_skill}).",
                    "context": f"Volunteer dispatch for {incident_meta['disaster_type']} response.",
                }
            )

        return messages

    def prepare_reporter_message(
        self,
        incident_meta: Dict[str, Any],
        priority: str,
        hospitals: Optional[List[Dict[str, Any]]],
        shelters: Optional[List[Dict[str, Any]]],
        mission_id: Optional[int],
    ) -> Dict[str, Any]:
        """Generate an acknowledgment and safety advisory update for the incident reporter."""
        incident_id_str = f"#{incident_meta['incident_id']}" if incident_meta["incident_id"] else "your report"
        subject = f"Emergency Services Update: Incident {incident_id_str} Acknowledged"

        nearest_shelter_note = ""
        if shelters and isinstance(shelters, list) and isinstance(shelters[0], dict):
            s_name = shelters[0].get("name", "Designated Shelter")
            s_dist = shelters[0].get("distance_km")
            dist_txt = f" (approx. {s_dist} km away)" if s_dist is not None else ""
            nearest_shelter_note = f"\n- Designated Emergency Shelter: {s_name}{dist_txt}"

        nearest_hospital_note = ""
        if hospitals and isinstance(hospitals, list) and isinstance(hospitals[0], dict):
            h_name = hospitals[0].get("name", "Nearest Hospital")
            h_dist = hospitals[0].get("straight_distance_km")
            dist_txt = f" (approx. {h_dist} km away)" if h_dist is not None else ""
            nearest_hospital_note = f"\n- Nearest Medical Facility: {h_name}{dist_txt}"

        body = (
            f"EMERGENCY RESPONSE STATUS UPDATE\n"
            f"Dear {incident_meta['reporter_name']},\n\n"
            f"Your report regarding the {incident_meta['disaster_type']} at {incident_meta['location']} "
            f"has been received and logged under Incident {incident_id_str}.\n"
            f"Assessment Priority: {priority}.\n"
            f"Emergency coordination is currently active.{nearest_hospital_note}{nearest_shelter_note}\n\n"
            f"Safety Guidance:\n"
            f"- Stay in a safe, structurally sound location and avoid hazardous areas.\n"
            f"- Keep phone lines clear for emergency communications.\n"
            f"- Await instructions from emergency first responders."
        )

        return {
            "mission_id": mission_id,
            "communication_status": self.COMMUNICATION_STATUS,
            "target": "incident_reporter",
            "recipient": incident_meta["reporter_name"],
            "contact": incident_meta["phone"],
            "channel": "sms",
            "subject": subject,
            "title": subject,
            "message": body,
            "priority": priority,
            "reason": f"Incident acknowledgment and safety update for {incident_meta['reporter_name']}.",
            "context": f"Public safety advisory for incident {incident_id_str} in {incident_meta['location']}.",
        }

    def generate_communications(
        self,
        incident: Any = None,
        assessment: Optional[Dict[str, Any]] = None,
        rescue_plan: Optional[Dict[str, Any]] = None,
        hospitals: Optional[List[Dict[str, Any]]] = None,
        shelters: Optional[List[Dict[str, Any]]] = None,
        volunteer_allocation: Optional[Dict[str, Any]] = None,
        mission_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Prepare all emergency communication actions across supported targets.

        Handles missing contacts, empty resource collections, and partial inputs safely.
        """
        incident_meta = self._extract_incident_metadata(incident)

        # Priority extraction
        priority = self._clean_text(
            self._value(assessment, "priority", self._value(rescue_plan, "priority")),
            default="MEDIUM",
        ).upper()

        reason = self._clean_text(
            self._value(assessment, "reason"),
            default="Emergency coordination initiated based on initial report.",
        )

        resources = self._value(assessment, "resources", self._value(rescue_plan, "required_resources", []))
        if not isinstance(resources, list):
            resources = []
        clean_resources = [str(r).strip() for r in resources if str(r).strip()]

        messages: List[Dict[str, Any]] = []

        # 1. Mission activation message for responders
        responder_msg = self.prepare_responder_message(
            incident_meta=incident_meta,
            priority=priority,
            reason=reason,
            resources=clean_resources,
            rescue_plan=rescue_plan,
            mission_id=mission_id,
        )
        messages.append(responder_msg)

        # 2. Hospital notification messages
        hospital_msgs = self.prepare_hospital_messages(
            hospitals=hospitals,
            incident_meta=incident_meta,
            priority=priority,
            mission_id=mission_id,
        )
        messages.extend(hospital_msgs)

        # 3. Shelter notification messages
        shelter_msgs = self.prepare_shelter_messages(
            shelters=shelters,
            incident_meta=incident_meta,
            priority=priority,
            mission_id=mission_id,
        )
        messages.extend(shelter_msgs)

        # 4. Volunteer deployment messages
        volunteer_msgs = self.prepare_volunteer_messages(
            volunteer_allocation=volunteer_allocation,
            incident_meta=incident_meta,
            priority=priority,
            mission_id=mission_id,
        )
        messages.extend(volunteer_msgs)

        # 5. Incident reporter status update
        reporter_msg = self.prepare_reporter_message(
            incident_meta=incident_meta,
            priority=priority,
            hospitals=hospitals,
            shelters=shelters,
            mission_id=mission_id,
        )
        messages.append(reporter_msg)

        targets = list(dict.fromkeys(msg["target"] for msg in messages))

        return {
            "mission_id": mission_id,
            "communication_status": self.COMMUNICATION_STATUS,
            "total_messages": len(messages),
            "messages": messages,
            "communications": messages,  # convenient alias
            "targets": targets,
            "summary": (
                f"Prepared {len(messages)} emergency communications across targets: "
                f"{', '.join(targets)} for mission #{mission_id or 'N/A'}."
            ),
        }

    # Aliases for flexible calling conventions
    prepare_communications = generate_communications

    def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Workflow execution compatibility runner."""
        return self.generate_communications(*args, **kwargs)
