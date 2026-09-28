"""Deterministic reflection agent for diagnosing rescue plan gaps and human feedback."""

from typing import Any


class ReflectionAgent:
    """Diagnoses failures, resource gaps, and reviewer feedback to guide replanning."""

    def reflect(
        self,
        mission: dict[str, Any],
        incident: dict[str, Any],
        feedback: str | None = None,
    ) -> dict[str, Any]:
        """Analyze existing rescue plan gaps and reviewer critique without LLM dependency."""
        rescue_plan = mission.get("rescue_plan_data") or {}
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
            if any(
                term in fb_lower
                for term in (
                    "volunteer",
                    "staff",
                    "personnel",
                    "team",
                    "skill",
                    "first-aid",
                    "rescue",
                )
            ):
                feedback_mentions_volunteers = True
            if any(
                term in fb_lower
                for term in (
                    "shelter",
                    "bed",
                    "housing",
                    "capacity",
                    "hall",
                    "camp",
                )
            ):
                feedback_mentions_shelters = True
            if any(
                term in fb_lower
                for term in (
                    "hospital",
                    "medical",
                    "doctor",
                    "ambulance",
                    "clinic",
                )
            ):
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
        }
