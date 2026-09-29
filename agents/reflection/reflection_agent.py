"""Reflection agent for diagnosing rescue plan gaps, reviewer feedback, and experience-based adaptation."""

import json
import logging
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from backend.database.connection import get_connection

logger = logging.getLogger(__name__)


@contextmanager
def _connection_scope(connection=None):
    if connection is not None:
        if callable(connection):
            conn = connection()
            try:
                yield conn
            finally:
                conn.close()
            return
        yield connection
        return

    with get_connection() as conn:
        yield conn


class ReflectionAgent:
    """Diagnoses failures, resource gaps, reviewer feedback, and retrieves past experiences to guide replanning."""

    def _ensure_tables(self, conn):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mission_reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mission_id INTEGER NOT NULL,
                incident_id INTEGER NOT NULL,
                disaster_type TEXT,
                location TEXT,
                outcome TEXT NOT NULL DEFAULT 'COMPLETED',
                reflection_summary TEXT,
                lessons_learned TEXT,
                resource_notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()

    def record_feedback_for_mission(self, mission_id: int, feedback_text: str, connection=None):
        """Record explicit coordinator critique for a mission."""
        with _connection_scope(connection) as conn:
            self._ensure_tables(conn)
            conn.execute(
                """
                INSERT INTO mission_reflections (mission_id, incident_id, outcome, reflection_summary, lessons_learned)
                VALUES (?, 0, 'FEEDBACK', ?, ?)
                """,
                (mission_id, feedback_text, f"Coordinator critique recorded: {feedback_text}"),
            )
            conn.commit()

    def reflect_on_completion(
        self,
        mission: Dict[str, Any],
        incident: Optional[Any] = None,
        connection=None,
    ) -> Dict[str, Any]:
        """Generate and persist an operational experience reflection upon mission completion."""
        mission_id = mission.get("mission_id") or mission.get("id") or 0
        incident_id = mission.get("incident_id") or getattr(incident, "id", 0) or 0

        disaster_type = getattr(incident, "disaster_type", None) or mission.get("disaster_type") or "Emergency"
        location = getattr(incident, "location", None) or mission.get("location") or "Tamil Nadu"
        people = getattr(incident, "people_affected", None) or mission.get("people_affected") or 0

        plan_data = mission.get("rescue_plan_data") or {}
        if isinstance(plan_data, str):
            try:
                plan_data = json.loads(plan_data)
            except Exception:
                plan_data = {}

        resources = plan_data.get("required_resources") or []
        res_str = ", ".join(resources) if resources else "Standard relief assets"

        summary = (
            f"Mission #{mission_id} ({disaster_type} at {location}): Response operations successfully "
            f"concluded for {people:,} affected citizens. Allocated resources ({res_str}) met field requirements."
        )
        lessons = (
            f"Prioritize rapid resource deployment ({res_str}) for future {disaster_type} incidents in {location}. "
            f"Maintain proactive shelter capacity and coordinated volunteer dispatch."
        )

        with _connection_scope(connection) as conn:
            self._ensure_tables(conn)
            conn.execute(
                """
                INSERT INTO mission_reflections (
                    mission_id, incident_id, disaster_type, location, outcome,
                    reflection_summary, lessons_learned, resource_notes
                ) VALUES (?, ?, ?, ?, 'COMPLETED', ?, ?, ?)
                """,
                (mission_id, incident_id, disaster_type, location, summary, lessons, res_str),
            )
            conn.commit()

        logger.info("Recorded completion reflection for Mission #%d (%s in %s)", mission_id, disaster_type, location)
        return {
            "mission_id": mission_id,
            "incident_id": incident_id,
            "disaster_type": disaster_type,
            "location": location,
            "summary": summary,
            "lessons_learned": lessons,
            "resource_notes": res_str,
        }

    def retrieve_similar_experiences(
        self,
        disaster_type: Optional[str] = None,
        location: Optional[str] = None,
        exclude_mission_id: Optional[int] = None,
        connection=None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve historical experiences/reflections from past incidents to inform current planning."""
        results: List[Dict[str, Any]] = []
        d_type = (disaster_type or "").strip().lower()
        loc = (location or "").strip().lower()

        with _connection_scope(connection) as conn:
            self._ensure_tables(conn)
            conn.row_factory = sqlite3.Row

            # 1. Query dedicated mission_reflections table
            query = """
                SELECT * FROM mission_reflections
                WHERE outcome IN ('COMPLETED', 'FEEDBACK')
            """
            params = []
            if exclude_mission_id:
                query += " AND mission_id != ?"
                params.append(exclude_mission_id)

            rows = conn.execute(query + " ORDER BY id DESC LIMIT 50", params).fetchall()
            for r in rows:
                r_dict = dict(r)
                r_dt = (r_dict.get("disaster_type") or "").lower()
                r_loc = (r_dict.get("location") or "").lower()

                # Match either disaster type or location
                if (d_type and d_type in r_dt) or (loc and loc in r_loc) or (not d_type and not loc):
                    results.append({
                        "mission_id": r_dict.get("mission_id"),
                        "incident_id": r_dict.get("incident_id"),
                        "disaster_type": r_dict.get("disaster_type"),
                        "location": r_dict.get("location"),
                        "summary": r_dict.get("reflection_summary"),
                        "lessons_learned": r_dict.get("lessons_learned"),
                        "source": "mission_reflections",
                    })
                    if len(results) >= limit:
                        break

            # 2. If fewer than desired reflections, supplement from completed missions in database
            if len(results) < limit:
                m_query = """
                    SELECT m.mission_id, m.incident_id, m.status, m.rescue_plan_data,
                           i.disaster_type, i.location, i.people_affected
                    FROM missions m
                    JOIN incidents i ON m.incident_id = i.id
                    WHERE m.status = 'COMPLETED'
                """
                m_params = []
                if exclude_mission_id:
                    m_query += " AND m.mission_id != ?"
                    m_params.append(exclude_mission_id)

                m_rows = conn.execute(m_query + " ORDER BY m.mission_id DESC LIMIT 50", m_params).fetchall()
                for mr in m_rows:
                    mr_dict = dict(mr)
                    mr_dt = (mr_dict.get("disaster_type") or "").lower()
                    mr_loc = (mr_dict.get("location") or "").lower()

                    if any(r["mission_id"] == mr_dict["mission_id"] for r in results):
                        continue

                    if (d_type and d_type in mr_dt) or (loc and loc in mr_loc) or (not d_type and not loc):
                        results.append({
                            "mission_id": mr_dict.get("mission_id"),
                            "incident_id": mr_dict.get("incident_id"),
                            "disaster_type": mr_dict.get("disaster_type"),
                            "location": mr_dict.get("location"),
                            "summary": f"Completed mission #{mr_dict['mission_id']} for {mr_dict.get('disaster_type')} in {mr_dict.get('location')}.",
                            "lessons_learned": f"Standard operational protocol for {mr_dict.get('disaster_type')} effectively safeguarded affected individuals.",
                            "source": "missions_history",
                        })
                        if len(results) >= limit:
                            break

        logger.info(
            "Retrieved %d past experiences for disaster=%s, location=%s",
            len(results), disaster_type, location
        )
        return results

    def reflect(
        self,
        mission: dict[str, Any],
        incident: dict[str, Any],
        feedback: str | None = None,
        connection=None,
    ) -> dict[str, Any]:
        """Analyze existing rescue plan gaps, reviewer critique, and past incident experiences."""
        rescue_plan = mission.get("rescue_plan_data") or {}
        if isinstance(rescue_plan, str):
            try:
                rescue_plan = json.loads(rescue_plan)
            except Exception:
                rescue_plan = {}

        existing_gaps = list(rescue_plan.get("resource_gaps") or [])
        clean_feedback = (
            feedback.strip()
            if isinstance(feedback, str) and feedback.strip()
            else None
        )

        # Detect specific gap categories
        unmet_skills = []
        volunteer_shortfall = False
        shelter_shortfall = False
        hospital_shortfall = False

        for gap in existing_gaps:
            gap_str = str(gap)
            if "unmet volunteer skill:" in gap_str.lower():
                skill_part = gap_str.split(":", 1)[-1].strip().rstrip(".")
                if skill_part and skill_part not in unmet_skills:
                    unmet_skills.append(skill_part)
            elif "volunteer shortfall:" in gap_str.lower():
                volunteer_shortfall = True
            elif "shelter" in gap_str.lower():
                shelter_shortfall = True
            elif "hospital" in gap_str.lower():
                hospital_shortfall = True

        # Human feedback analysis
        feedback_mentions_volunteers = False
        feedback_mentions_shelters = False
        feedback_mentions_hospitals = False
        if clean_feedback:
            fb_lower = clean_feedback.lower()
            if any(term in fb_lower for term in ("volunteer", "staff", "personnel", "team", "skill", "first-aid", "rescue", "boat")):
                feedback_mentions_volunteers = True
            if any(term in fb_lower for term in ("shelter", "bed", "housing", "capacity", "hall", "camp")):
                feedback_mentions_shelters = True
            if any(term in fb_lower for term in ("hospital", "medical", "doctor", "ambulance", "clinic")):
                feedback_mentions_hospitals = True

        volunteer_plan_existed = bool(rescue_plan.get("volunteer_plan"))
        reallocate_volunteers = bool(
            unmet_skills
            or volunteer_shortfall
            or feedback_mentions_volunteers
            or (mission.get("status") == "REPLANNING" and volunteer_plan_existed)
        )
        retry_shelters = bool(shelter_shortfall or feedback_mentions_shelters)
        retry_hospitals = bool(hospital_shortfall or feedback_mentions_hospitals)

        strategy_adjustments = {
            "reallocate_volunteers": reallocate_volunteers,
            "retry_shelters": retry_shelters,
            "retry_hospitals": retry_hospitals,
            "unmet_skills": unmet_skills,
            "feedback_noted": clean_feedback is not None,
        }

        # Build diagnostic description
        diagnosis_parts = []
        if unmet_skills:
            diagnosis_parts.append(
                f"Unmet volunteer skills identified: {', '.join(unmet_skills)}."
            )
        if volunteer_shortfall:
            diagnosis_parts.append("Volunteer headcount quota was unmet.")
        if shelter_shortfall:
            diagnosis_parts.append("Shelter capacity was insufficient or missing.")
        if hospital_shortfall:
            diagnosis_parts.append("Medical/hospital support options were lacking.")
        if clean_feedback:
            diagnosis_parts.append(f"Reviewer provided feedback: '{clean_feedback}'.")

        # Retrieve relevant past experiences
        disaster_type = getattr(incident, "disaster_type", None) or (incident.get("disaster_type") if isinstance(incident, dict) else None)
        location = getattr(incident, "location", None) or (incident.get("location") if isinstance(incident, dict) else None)
        past_experiences = self.retrieve_similar_experiences(
            disaster_type=disaster_type,
            location=location,
            exclude_mission_id=mission.get("mission_id"),
            connection=connection,
        )

        if past_experiences:
            diagnosis_parts.append(
                f"Experience-based memory retrieved {len(past_experiences)} past similar incident outcome(s)."
            )

        if not diagnosis_parts:
            diagnosis = "No specific resource gaps or reviewer feedback identified; plan may reflect current available capacity."
            summary = "Reflection complete: no actionable resource gaps detected."
        else:
            diagnosis = " ".join(diagnosis_parts)
            summary = (
                f"Reflection identified {len(existing_gaps)} gap(s)"
                f"{' and incorporated reviewer feedback' if clean_feedback else ''}. "
                f"Strategy: volunteer reallocation={'yes' if reallocate_volunteers else 'no'}, "
                f"shelter retry={'yes' if retry_shelters else 'no'}, "
                f"hospital retry={'yes' if retry_hospitals else 'no'}."
            )

        return {
            "reflection_status": "completed",
            "gaps": existing_gaps,
            "human_feedback": clean_feedback,
            "diagnosis": diagnosis,
            "strategy_adjustments": strategy_adjustments,
            "reflection_summary": summary,
            "past_experiences": past_experiences,
        }
