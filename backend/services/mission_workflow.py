"""Minimal LangGraph orchestration for the disaster-response agent sequence."""

import logging
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

logger = logging.getLogger(__name__)

from backend.models.incident_model import get_incident_by_id
from backend.models.mission_model import (
    create_mission,
    get_mission_by_id,
    update_approval_status,
    update_mission_state,
    update_mission_status,
)
from backend.models.volunteer_model import (
    complete_incident_volunteers,
    release_incident_volunteers,
)


class MissionWorkflowState(TypedDict, total=False):
    """Shared state accumulated by the initial mission workflow."""

    incident: Any
    incident_coordinates: tuple[float, float]
    incident_district: str
    required_volunteer_skills: str | list[str] | None
    required_volunteer_count: int
    assessment: dict
    rag_context: dict
    hospitals: list[dict]
    shelters: list[dict]
    volunteer_allocation: dict
    rescue_plan: dict
    mission_id: int
    mission: dict
    status: str
    error: str


class MissionWorkflow:
    """Compose existing agents without duplicating their implementation logic."""

    def __init__(
        self,
        assessment_agent=None,
        hospital_agent=None,
        shelter_agent=None,
        volunteer_agent=None,
        planning_agent=None,
        mission_connection=None,
        rag_agent=None,
        communication_agent=None,
        reflection_agent=None,
        notification_service=None,
    ):
        self.assessment_agent = assessment_agent
        self.rag_agent = rag_agent
        self.hospital_agent = hospital_agent
        self.shelter_agent = shelter_agent
        self.volunteer_agent = volunteer_agent
        self.planning_agent = planning_agent
        self.mission_connection = mission_connection
        self.communication_agent = communication_agent
        self.reflection_agent = reflection_agent
        self.notification_service = notification_service

    def _assessment_agent(self):
        if self.assessment_agent is None:
            from agents.assessment.assessment_agent import AssessmentAgent

            self.assessment_agent = AssessmentAgent()
        return self.assessment_agent

    def _hospital_agent(self):
        if self.hospital_agent is None:
            from agents.hospital.hospital_agent import HospitalAgent

            self.hospital_agent = HospitalAgent()
        return self.hospital_agent

    def _rag_agent(self):
        if self.rag_agent is None:
            from rag.agentic_retriever import AgenticRAG

            self.rag_agent = AgenticRAG()
        return self.rag_agent

    def _shelter_agent(self):
        if self.shelter_agent is None:
            from agents.shelter_finder_agent import ShelterFinderAgent

            self.shelter_agent = ShelterFinderAgent(connection=self.mission_connection)
        return self.shelter_agent

    def _volunteer_agent(self):
        if self.volunteer_agent is None:
            from agents.volunteer.volunteer_agent import VolunteerAllocationAgent

            self.volunteer_agent = VolunteerAllocationAgent(connection=self.mission_connection)
        return self.volunteer_agent

    def _planning_agent(self):
        if self.planning_agent is None:
            from agents.planning.planning_agent import PlanningAgent

            self.planning_agent = PlanningAgent()
        return self.planning_agent

    def _communication_agent(self):
        if self.communication_agent is None:
            from agents.communication.communication_agent import CommunicationAgent

            self.communication_agent = CommunicationAgent()
        return self.communication_agent

    def _reflection_agent(self):
        if self.reflection_agent is None:
            from agents.reflection.reflection_agent import ReflectionAgent

            self.reflection_agent = ReflectionAgent()
        return self.reflection_agent

    def _notification_service(self):
        if self.notification_service is None:
            from backend.services.notification_service import NotificationService

            self.notification_service = NotificationService()
        return self.notification_service

    @staticmethod
    def _blocked(state):
        return {"status": "blocked"} if state.get("error") else None

    @staticmethod
    def _failure(node_name, error):
        return {
            "status": "failed",
            "error": f"{node_name} node failed: {error}",
        }

    @staticmethod
    def _incident_value(incident, key, default=None):
        if isinstance(incident, dict):
            return incident.get(key, default)
        return getattr(incident, key, default)

    def assessment_node(self, state: MissionWorkflowState):
        """Run the existing assessment agent."""
        if blocked := self._blocked(state):
            return blocked
        try:
            return {
                "assessment": self._assessment_agent().assess(state["incident"]),
                "status": "assessed",
            }
        except Exception as error:
            return self._failure("assessment", error)

    def hospital_node(self, state: MissionWorkflowState):
        """Run the existing hospital lookup using the incident location."""
        if blocked := self._blocked(state):
            return blocked
        try:
            location = self._incident_value(state["incident"], "location")
            if not isinstance(location, str) or not location.strip():
                raise ValueError("incident location is required")
            return {
                "hospitals": self._hospital_agent().get_nearby_hospitals(location),
                "status": "hospitals_ready",
            }
        except Exception as error:
            return self._failure("hospital", error)

    def rag_node(self, state: MissionWorkflowState):
        """Retrieve optional disaster guidance after assessment is available."""
        if blocked := self._blocked(state):
            return blocked
        try:
            return {
                "rag_context": self._rag_agent().retrieve_for_incident(
                    state["incident"], state["assessment"]
                ),
                "status": "rag_ready",
            }
        except Exception as error:
            return self._failure("rag", error)

    def shelter_node(self, state: MissionWorkflowState):
        """Run the existing shelter finder with caller-provided coordinates."""
        if blocked := self._blocked(state):
            return blocked
        try:
            coordinates = state.get("incident_coordinates")
            if not isinstance(coordinates, (tuple, list)) or len(coordinates) != 2:
                district = state.get("incident_district") or self._incident_value(state.get("incident"), "location")
                from backend.services.maps_service import geocode_location
                geo = geocode_location(str(district)) if district else None
                if geo:
                    coordinates = (geo["latitude"], geo["longitude"])
                else:
                    raise ValueError("incident_coordinates must contain latitude and longitude")
            latitude, longitude = coordinates
            people_affected = self._incident_value(state["incident"], "people_affected")
            if not isinstance(people_affected, int) or people_affected < 1:
                raise ValueError("incident people_affected must be a positive integer")
            return {
                "shelters": self._shelter_agent().find_nearest_shelters(
                    latitude,
                    longitude,
                    required_capacity=people_affected,
                    incident_district=state.get("incident_district"),
                    connection=self.mission_connection,
                ),
                "status": "shelters_ready",
            }
        except Exception as error:
            return self._failure("shelter", error)

    def volunteer_node(self, state: MissionWorkflowState):
        """Run the existing deterministic volunteer allocation agent."""
        if blocked := self._blocked(state):
            return blocked
        try:
            incident_id = self._incident_value(state["incident"], "id")
            district = state.get("incident_district")
            if not isinstance(incident_id, int) or incident_id < 1:
                raise ValueError("incident must provide a positive integer id")
            if not isinstance(district, str) or not district.strip():
                raise ValueError("incident_district is required")
            assessment = state.get("assessment") or {}
            resources = assessment.get("resources")
            disaster_type = self._incident_value(state["incident"], "disaster_type")

            return {
                "volunteer_allocation": self._volunteer_agent().allocate(
                    incident_id,
                    district,
                    required_skills=state.get("required_volunteer_skills"),
                    required_count=state.get("required_volunteer_count", 1),
                    resources=resources,
                    disaster_type=disaster_type,
                    connection=self.mission_connection,
                ),
                "status": "volunteers_ready",
            }
        except Exception as error:
            return self._failure("volunteer", error)

    def planning_node(self, state: MissionWorkflowState):
        """Compose supplied component outputs into the existing rescue-plan format with experience-based adaptation."""
        if blocked := self._blocked(state):
            return blocked
        try:
            disaster_type = self._incident_value(state["incident"], "disaster_type") or ""
            location = state.get("incident_district") or self._incident_value(state["incident"], "location") or ""
            past_experiences = []
            try:
                past_experiences = self._reflection_agent().retrieve_similar_experiences(
                    disaster_type=disaster_type,
                    location=location,
                    exclude_mission_id=state.get("mission_id"),
                    connection=self.mission_connection,
                )
            except Exception as exp_err:
                logger.warning("Could not retrieve past experiences for planning: %s", exp_err)

            plan = self._planning_agent().create_plan(
                incident=state["incident"],
                assessment=state["assessment"],
                hospitals=state.get("hospitals", []),
                shelters=state.get("shelters", []),
                volunteer_allocation=state.get("volunteer_allocation"),
                rag_context=state.get("rag_context"),
                past_experiences=past_experiences,
            )
            logger.info("Node: Planning completed | status=planned | past_experiences=%d", len(past_experiences))
            return {
                "rescue_plan": plan,
                "status": "planned",
            }
        except Exception as error:
            logger.error("Node: Planning failed: %s", error)
            return self._failure("planning", error)

    def mission_persistence_node(self, state: MissionWorkflowState):
        """Persist the completed plan, notify reporter of intake, and stop at the approval boundary."""
        if blocked := self._blocked(state):
            return blocked
        try:
            incident_id = self._incident_value(state["incident"], "id")
            if not isinstance(incident_id, int) or incident_id < 1:
                raise ValueError("incident must provide a positive integer id")

            mission = create_mission(
                incident_id,
                assessment_data=state["assessment"],
                rescue_plan_data=state["rescue_plan"],
                connection=self.mission_connection,
            )
            mission = update_mission_status(
                mission["mission_id"],
                "AWAITING_APPROVAL",
                connection=self.mission_connection,
            )
            if mission is None:
                raise RuntimeError("mission could not be updated for approval")

            logger.info(
                "Mission saved | mission_id=%d | status=AWAITING_APPROVAL | approval_status=PENDING",
                mission["mission_id"],
            )

            # Send clean initial acknowledgment email to reporter (status: Awaiting approval)
            try:
                self._notification_service().dispatch_reporter_notification(
                    incident=state["incident"],
                    mission_id=mission["mission_id"],
                    mission_status="AWAITING_APPROVAL",
                    approval_status="PENDING",
                    assessment=state.get("assessment"),
                    rescue_plan=state.get("rescue_plan"),
                    hospitals=state.get("hospitals"),
                    shelters=state.get("shelters"),
                    volunteer_allocation=state.get("volunteer_allocation"),
                )
            except Exception as notif_err:
                logger.warning("Reporter initial notification error: %s", notif_err)

            return {
                "mission_id": mission["mission_id"],
                "mission": mission,
                "status": "awaiting_approval",
            }
        except Exception as error:
            logger.error("Node: Mission persistence failed: %s", error)
            return self._failure("mission persistence", error)

    def _get_pending_mission(self, mission_id):
        """Return a mission only when it is at the explicit approval boundary."""
        if not isinstance(mission_id, int) or mission_id < 1:
            raise ValueError("mission_id must be a positive integer.")
        mission = get_mission_by_id(mission_id, connection=self.mission_connection)
        if mission is None:
            raise ValueError(f"Mission {mission_id} does not exist.")
        if (
            mission["status"] != "AWAITING_APPROVAL"
            or mission["approval_status"] != "PENDING"
        ):
            raise ValueError(f"Mission {mission_id} is not awaiting approval.")
        return mission

    def approve_mission(self, mission_id):
        """Approve a pending mission, reserve shelter, prepare communications, and transition to ACTIVE."""
        pending_mission = self._get_pending_mission(mission_id)
        incident_id = pending_mission.get("incident_id")
        incident = get_incident_by_id(incident_id, connection=self.mission_connection)
        if incident is None:
            raise RuntimeError(
                f"Incident {incident_id} not found for mission {mission_id}."
            )

        assessment_data = pending_mission.get("assessment_data") or {}
        rescue_plan_data = pending_mission.get("rescue_plan_data") or {}
        hospitals = rescue_plan_data.get("hospital_plan", [])
        shelters = rescue_plan_data.get("shelter_plan", [])
        volunteer_plan = rescue_plan_data.get("volunteer_plan", [])
        volunteer_allocation = {"assignments": volunteer_plan}

        # Shelter reservation:
        shelter_reserved = False
        reserved_shelter_id = None
        reserved_capacity = 0
        if shelters and isinstance(shelters, list) and len(shelters) > 0:
            primary_shelter = shelters[0]
            shelter_id = primary_shelter.get("id")
            people_affected = incident.get("people_affected")
            if (
                shelter_id is not None
                and isinstance(people_affected, int)
                and people_affected > 0
            ):
                res = self._shelter_agent().update_occupancy(
                    shelter_id, people_affected, connection=self.mission_connection
                )
                if not res.get("success"):
                    raise ValueError(
                        f"Shelter reservation failed for mission {mission_id}: {res.get('message', 'Capacity not available')}"
                    )
                shelter_reserved = True
                reserved_shelter_id = shelter_id
                reserved_capacity = people_affected
                rescue_plan_data["shelter_reservation"] = {
                    "shelter_id": shelter_id,
                    "shelter_name": primary_shelter.get("name"),
                    "reserved_capacity": people_affected,
                    "status": "reserved",
                }
                update_mission_state(
                    mission_id,
                    rescue_plan_data=rescue_plan_data,
                    connection=self.mission_connection,
                )

        try:
            communications = self._communication_agent().generate_communications(
                incident=incident,
                assessment=assessment_data,
                rescue_plan=rescue_plan_data,
                hospitals=hospitals,
                shelters=shelters,
                volunteer_allocation=volunteer_allocation,
                mission_id=mission_id,
            )
        except Exception as error:
            if shelter_reserved and reserved_shelter_id is not None:
                self._shelter_agent().release_occupancy(
                    reserved_shelter_id,
                    reserved_capacity,
                    connection=self.mission_connection,
                )
                rescue_plan_data.pop("shelter_reservation", None)
                update_mission_state(
                    mission_id,
                    rescue_plan_data=rescue_plan_data,
                    connection=self.mission_connection,
                )
            raise RuntimeError(
                f"Communication preparation failed for mission {mission_id}: {error}"
            ) from error

        if not isinstance(communications, dict) or communications.get("communication_status") != "prepared":
            if shelter_reserved and reserved_shelter_id is not None:
                self._shelter_agent().release_occupancy(
                    reserved_shelter_id,
                    reserved_capacity,
                    connection=self.mission_connection,
                )
                rescue_plan_data.pop("shelter_reservation", None)
                update_mission_state(
                    mission_id,
                    rescue_plan_data=rescue_plan_data,
                    connection=self.mission_connection,
                )
            raise RuntimeError(
                f"Communication preparation failed for mission {mission_id}: invalid status."
            )

        # Dispatch notifications (notification failures MUST NOT undo approval)
        notification_dispatch = None
        try:
            notification_dispatch = self._notification_service().dispatch_communications(communications)
        except Exception as error:
            notification_dispatch = {
                "dispatch_status": "failed",
                "dispatch_mode": getattr(self._notification_service(), "mode", "UNKNOWN"),
                "total_messages": len(communications.get("messages", [])),
                "sent": 0,
                "simulated": 0,
                "failed": len(communications.get("messages", [])),
                "skipped": 0,
                "error": f"Notification dispatch error: {error}",
                "results": [],
            }

        approved_mission = update_approval_status(
            mission_id,
            "APPROVED",
            connection=self.mission_connection,
        )
        if approved_mission is None:
            raise RuntimeError(f"Mission {mission_id} approval update failed.")
        active_mission = update_mission_status(
            mission_id,
            "ACTIVE",
            connection=self.mission_connection,
        )
        if active_mission is None:
            raise RuntimeError(f"Mission {mission_id} activation failed.")

        # Dispatch clean operational status notification to reporter (status: ACTIVE)
        try:
            self._notification_service().dispatch_reporter_notification(
                incident=incident,
                mission_id=mission_id,
                mission_status="ACTIVE",
                approval_status="APPROVED",
                assessment=assessment_data,
                rescue_plan=rescue_plan_data,
                hospitals=hospitals,
                shelters=shelters,
                volunteer_allocation=volunteer_allocation,
            )
        except Exception as notif_err:
            logger.warning("Reporter active notification error: %s", notif_err)

        result = dict(active_mission)
        result["mission"] = active_mission
        result["communications"] = communications
        result["notification_dispatch"] = notification_dispatch
        return result

    def reject_mission(self, mission_id, feedback=None, reason=None):
        """Reject a pending mission, release volunteers, and transition to REPLANNING."""
        if feedback is None and reason is not None:
            feedback = reason
        pending_mission = self._get_pending_mission(mission_id)
        incident_id = pending_mission.get("incident_id")
        released_volunteers = release_incident_volunteers(
            incident_id, connection=self.mission_connection
        )

        clean_feedback = (
            feedback.strip()
            if isinstance(feedback, str) and feedback.strip()
            else None
        )
        if clean_feedback:
            rescue_plan_data = pending_mission.get("rescue_plan_data") or {}
            rescue_plan_data["rejection_feedback"] = clean_feedback
            update_mission_state(
                mission_id,
                rescue_plan_data=rescue_plan_data,
                connection=self.mission_connection,
            )

        rejected_mission = update_approval_status(
            mission_id,
            "REJECTED",
            connection=self.mission_connection,
        )
        if rejected_mission is None:
            raise RuntimeError(f"Mission {mission_id} rejection update failed.")
        replanning_mission = update_mission_status(
            mission_id,
            "REPLANNING",
            connection=self.mission_connection,
        )
        if replanning_mission is None:
            raise RuntimeError(f"Mission {mission_id} replanning update failed.")

        # Dispatch clean notification to reporter (status: REPLANNING)
        try:
            inc_obj = get_incident_by_id(incident_id, connection=self.mission_connection)
            self._notification_service().dispatch_reporter_notification(
                incident=inc_obj,
                mission_id=mission_id,
                mission_status="REPLANNING",
                approval_status="REJECTED",
                assessment=pending_mission.get("assessment_data"),
                rescue_plan=pending_mission.get("rescue_plan_data"),
            )
        except Exception as notif_err:
            logger.warning("Reporter rejection notification error: %s", notif_err)

        result = dict(replanning_mission)
        result["mission"] = replanning_mission
        result["released_volunteers"] = released_volunteers
        if clean_feedback:
            result["feedback"] = clean_feedback
        return result

    def replan_mission(self, mission_id, feedback=None, additional_feedback=None):
        """Reflect on identified gaps and feedback to generate a revised rescue plan."""
        if feedback is None and additional_feedback is not None:
            feedback = additional_feedback
        if not isinstance(mission_id, int) or mission_id < 1:
            raise ValueError("mission_id must be a positive integer.")
        mission = get_mission_by_id(mission_id, connection=self.mission_connection)
        if mission is None:
            raise ValueError(f"Mission {mission_id} does not exist.")
        if mission.get("status") != "REPLANNING":
            raise ValueError(
                f"Mission {mission_id} is not in REPLANNING status (current status: {mission.get('status')})."
            )

        incident_id = mission.get("incident_id")
        incident = get_incident_by_id(incident_id, connection=self.mission_connection)
        if incident is None:
            raise RuntimeError(
                f"Incident {incident_id} not found for mission {mission_id}."
            )

        assessment_data = mission.get("assessment_data") or {}
        rescue_plan_data = mission.get("rescue_plan_data") or {}

        clean_feedback = (
            feedback.strip()
            if isinstance(feedback, str) and feedback.strip()
            else None
        )
        effective_feedback = clean_feedback or rescue_plan_data.get("rejection_feedback")

        # 1. Run ReflectionAgent
        reflection = self._reflection_agent().reflect(
            mission, incident, feedback=effective_feedback
        )

        # 2. Targeted resource reallocation using existing agents
        adjustments = reflection.get("strategy_adjustments", {})
        volunteer_alloc = {"assignments": rescue_plan_data.get("volunteer_plan", [])}

        if adjustments.get("reallocate_volunteers"):
            raw_district = incident.get("district") or incident.get("location") or "Chennai"
            district = raw_district.split(",")[-1].strip() if "," in raw_district else raw_district.strip()

            required_skills = adjustments.get("unmet_skills")
            if not required_skills:
                required_skills = assessment_data.get("resources")

            required_count = len(rescue_plan_data.get("volunteer_plan", [])) or 1
            try:
                volunteer_alloc = self._volunteer_agent().allocate(
                    incident_id,
                    district,
                    required_skills=required_skills,
                    required_count=required_count,
                    resources=assessment_data.get("resources"),
                    disaster_type=incident.get("disaster_type"),
                    connection=self.mission_connection,
                )
            except Exception:
                volunteer_alloc = {"assignments": rescue_plan_data.get("volunteer_plan", [])}

        hospitals = rescue_plan_data.get("hospital_plan", [])
        shelters = rescue_plan_data.get("shelter_plan", [])
        rag_context = rescue_plan_data.get("rag_context")
        past_experiences = reflection.get("past_experiences") or []

        # 3. Create revised plan with PlanningAgent
        revised_plan = self._planning_agent().create_plan(
            incident=incident,
            assessment=assessment_data,
            hospitals=hospitals,
            shelters=shelters,
            volunteer_allocation=volunteer_alloc,
            rag_context=rag_context,
            past_experiences=past_experiences,
        )

        # 4. Embed reflection in rescue_plan_data
        revised_plan["reflection"] = reflection
        if effective_feedback:
            revised_plan["rejection_feedback"] = effective_feedback

        # 5. Persist revised plan and transition state
        update_mission_state(
            mission_id,
            rescue_plan_data=revised_plan,
            connection=self.mission_connection,
        )
        update_approval_status(
            mission_id,
            "PENDING",
            connection=self.mission_connection,
        )
        replanned_mission = update_mission_status(
            mission_id,
            "AWAITING_APPROVAL",
            connection=self.mission_connection,
        )
        if replanned_mission is None:
            raise RuntimeError(f"Mission {mission_id} replanning failed.")

        result = dict(replanned_mission)
        result["mission"] = replanned_mission
        result["reflection"] = reflection
        return result

    def complete_mission(self, mission_id):
        """Mark an active mission as completed and release assigned volunteers and shelter capacity."""
        if not isinstance(mission_id, int) or mission_id < 1:
            raise ValueError("mission_id must be a positive integer.")
        mission = get_mission_by_id(mission_id, connection=self.mission_connection)
        if mission is None:
            raise ValueError(f"Mission {mission_id} does not exist.")
        if mission.get("status") != "ACTIVE":
            raise ValueError(
                f"Mission {mission_id} is not active (current status: {mission.get('status')})."
            )

        # Shelter release:
        rescue_plan_data = mission.get("rescue_plan_data") or {}
        shelter_reservation = rescue_plan_data.get("shelter_reservation")
        released_shelter = None
        if (
            isinstance(shelter_reservation, dict)
            and shelter_reservation.get("status") == "reserved"
        ):
            shelter_id = shelter_reservation.get("shelter_id")
            reserved_capacity = shelter_reservation.get("reserved_capacity", 0)
            if shelter_id is not None and reserved_capacity > 0:
                self._shelter_agent().release_occupancy(
                    shelter_id,
                    reserved_capacity,
                    connection=self.mission_connection,
                )
            shelter_reservation["status"] = "released"
            rescue_plan_data["shelter_reservation"] = shelter_reservation
            update_mission_state(
                mission_id,
                rescue_plan_data=rescue_plan_data,
                connection=self.mission_connection,
            )
            released_shelter = shelter_reservation

        incident_id = mission.get("incident_id")
        completed_volunteers = complete_incident_volunteers(
            incident_id, connection=self.mission_connection
        )

        completed_mission = update_mission_status(
            mission_id,
            "COMPLETED",
            connection=self.mission_connection,
        )
        if completed_mission is None:
            raise RuntimeError(f"Mission {mission_id} completion failed.")

        # Record operational experience reflection upon mission completion
        incident = None
        try:
            incident = get_incident_by_id(incident_id, connection=self.mission_connection)
            self._reflection_agent().reflect_on_completion(
                mission=completed_mission,
                incident=incident,
                connection=self.mission_connection,
            )
        except Exception as ref_err:
            logger.warning("Completion reflection error: %s", ref_err)

        # Send completion notification to reporter (status: Completed)
        try:
            self._notification_service().dispatch_reporter_notification(
                incident=incident,
                mission_id=mission_id,
                mission_status="COMPLETED",
                approval_status="APPROVED",
                assessment=completed_mission.get("assessment_data"),
                rescue_plan=completed_mission.get("rescue_plan_data"),
            )
        except Exception as notif_err:
            logger.warning("Reporter completion notification error: %s", notif_err)

        result = dict(completed_mission)
        result["mission"] = completed_mission
        result["completed_volunteers"] = completed_volunteers
        if released_shelter is not None:
            result["released_shelter"] = released_shelter
        return result

    def build_graph(self):
        """Construct the workflow through the explicit approval boundary."""
        graph = StateGraph(MissionWorkflowState)
        graph.add_node("assessment", self.assessment_node)
        graph.add_node("rag", self.rag_node)
        graph.add_node("hospital", self.hospital_node)
        graph.add_node("shelter", self.shelter_node)
        graph.add_node("volunteer", self.volunteer_node)
        graph.add_node("planning", self.planning_node)
        graph.add_node("mission_persistence", self.mission_persistence_node)
        graph.add_edge(START, "assessment")
        graph.add_edge("assessment", "rag")
        graph.add_edge("rag", "hospital")
        graph.add_edge("hospital", "shelter")
        graph.add_edge("shelter", "volunteer")
        graph.add_edge("volunteer", "planning")
        graph.add_edge("planning", "mission_persistence")
        graph.add_edge("mission_persistence", END)
        return graph.compile()

    def run(self, initial_state: MissionWorkflowState):
        """Execute the graph and return the accumulated mission workflow state."""
        return self.build_graph().invoke(initial_state)
