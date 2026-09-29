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
        incident_meta: Optional[Dict[str, Any]] = None,
        priority: str = "HIGH",
        hospitals: Optional[List[Dict[str, Any]]] = None,
        shelters: Optional[List[Dict[str, Any]]] = None,
        mission_id: Optional[int] = None,
        mission_status: str = "AWAITING_APPROVAL",
        approval_status: str = "PENDING",
        assessment: Optional[Dict[str, Any]] = None,
        volunteer_allocation: Optional[Dict[str, Any]] = None,
        rescue_plan: Optional[Dict[str, Any]] = None,
        incident: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Generate an acknowledgment and clean operational status update for the incident reporter."""
        if incident_meta is None and incident is not None:
            incident_meta = self._extract_incident_metadata(incident)
        elif incident_meta is None:
            incident_meta = self._extract_incident_metadata({})
        elif not isinstance(incident_meta, dict) or "disaster_type" not in incident_meta:
            incident_meta = self._extract_incident_metadata(incident_meta)

        m_id_str = f"{mission_id}" if mission_id else "PENDING"
        disaster_type = incident_meta.get("disaster_type", "Emergency")
        location = incident_meta.get("location", "Tamil Nadu")
        people_affected = incident_meta.get("people_affected", 1)

        # Priority resolution
        if assessment and isinstance(assessment, dict) and assessment.get("priority"):
            priority = str(assessment["priority"]).upper().strip()
        else:
            priority = (priority or "HIGH").upper().strip()

        # Mission status and approval resolution
        norm_m_status = (mission_status or "AWAITING_APPROVAL").upper().strip()
        norm_app_status = (approval_status or "PENDING").upper().strip()

        if norm_m_status in ("AWAITING_APPROVAL", "CREATED", "PENDING"):
            status_text = "Awaiting approval"
            approval_text = "Awaiting approval"
            eta_text = "15 - 25 mins (approximate arrival window once approved)"
            vol_text = "Volunteer assistance on standby"
        elif norm_m_status in ("ACTIVE", "APPROVED"):
            status_text = "ACTIVE"
            approval_text = "Approved"
            eta_text = "15 - 25 mins"
            vol_text = "Rescue team assigned"
        elif norm_m_status in ("REPLANNING", "REJECTED"):
            status_text = "REPLANNING"
            approval_text = "Rejected"
            eta_text = "Under review (replanning deployment)"
            vol_text = "Volunteer assistance on standby"
        elif norm_m_status in ("COMPLETED", "RESOLVED"):
            status_text = "COMPLETED"
            approval_text = "Approved"
            eta_text = "Completed"
            vol_text = "Rescue operations completed"
        else:
            status_text = norm_m_status.title()
            approval_text = norm_app_status.title()
            eta_text = "15 - 25 mins"
            vol_text = "Rescue team assigned"

        # Shelter name
        shelter_name = "Assigned District Relief Centre"
        if shelters and isinstance(shelters, list) and len(shelters) > 0 and isinstance(shelters[0], dict):
            s = shelters[0]
            s_name = s.get("name") or shelter_name
            s_dist = s.get("district", "")
            shelter_name = f"{s_name} ({s_dist})" if s_dist else s_name

        # Hospital name
        hospital_name = "District General Hospital (Standby)"
        if hospitals and isinstance(hospitals, list) and len(hospitals) > 0 and isinstance(hospitals[0], dict):
            h = hospitals[0]
            h_name = h.get("name") or hospital_name
            h_dist = h.get("district", "")
            hospital_name = f"{h_name} ({h_dist})" if h_dist else h_name

        # Resources string
        res_list = []
        if assessment and isinstance(assessment, dict) and assessment.get("resources"):
            res_list = assessment["resources"]
        elif rescue_plan and isinstance(rescue_plan, dict) and rescue_plan.get("required_resources"):
            res_list = rescue_plan["required_resources"]
        res_str = ", ".join(res_list) if res_list else "Rapid Assessment & Relief Team"

        # AI assessment explanation
        ai_assessment_text = ""
        if assessment and isinstance(assessment, dict) and assessment.get("reason"):
            ai_assessment_text = str(assessment["reason"]).strip()
        elif rescue_plan and isinstance(rescue_plan, dict) and rescue_plan.get("risk_notes"):
            notes = [n for n in rescue_plan["risk_notes"] if not str(n).startswith("[Experience")]
            if notes:
                ai_assessment_text = str(notes[0]).strip()
        if not ai_assessment_text:
            ai_assessment_text = (
                f"Emergency incident response for {disaster_type} at {location} "
                f"evaluated with {priority} priority based on {people_affected} affected citizens."
            )

        subject = f"EMERGENCY RESPONSE: Mission #{m_id_str} — {disaster_type} ({location})"

        body = (
            f"EMERGENCY RESPONSE\n\n"
            f"Mission #{m_id_str}\n\n"
            f"{disaster_type} — {location}\n\n"
            f"Priority:\n"
            f"{priority}\n\n"
            f"Incident Status:\n"
            f"{status_text}\n\n"
            f"Human Approval:\n"
            f"{approval_text}\n\n"
            f"Rescue / Response ETA:\n"
            f"{eta_text}\n\n"
            f"Shelter:\n"
            f"{shelter_name}\n\n"
            f"Hospital:\n"
            f"{hospital_name}\n\n"
            f"Volunteer / Rescue Team:\n"
            f"{vol_text}\n\n"
            f"People Affected:\n"
            f"{people_affected}\n\n"
            f"Required/Assigned Resources:\n"
            f"{res_str}\n\n"
            f"AI Assessment:\n"
            f"{ai_assessment_text}\n\n"
            f"Helpline:\n"
            f"1070\n\n"
            f"Important Instructions:\n"
            f"Please follow local authority and emergency coordinator instructions."
        )

        return {
            "mission_id": mission_id,
            "communication_status": self.COMMUNICATION_STATUS,
            "target": "incident_reporter",
            "recipient": incident_meta.get("reporter_name", "Emergency Reporter"),
            "contact": incident_meta.get("phone"),
            "channel": "email",
            "subject": subject,
            "title": subject,
            "message": body,
            "body": body,
            "priority": priority,
            "reason": f"Operational status update for mission #{m_id_str}.",
            "context": f"Public emergency update for {disaster_type} in {location}.",
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
            mission_status="ACTIVE",
            approval_status="APPROVED",
            assessment=assessment,
            volunteer_allocation=volunteer_allocation,
            rescue_plan=rescue_plan,
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
