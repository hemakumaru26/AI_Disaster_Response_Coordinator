import json
import logging
import re
from pathlib import Path

from backend.services.llm_service import get_llm
from backend.services.scoring_service import calculate_severity

logger = logging.getLogger(__name__)


class AssessmentAgent:

    def __init__(self):
        self.llm = get_llm()

        prompt_path = (
            Path(__file__).resolve()
            .parents[2]
            / "prompts"
            / "assessment.txt"
        )

        with open(prompt_path, "r", encoding="utf-8") as file:
            self.prompt_template = file.read()

    @staticmethod
    def _deterministic_fallback(incident):
        """Produce a valid, domain-aware assessment when the LLM is unavailable or times out."""
        severity_score = calculate_severity(incident)

        disaster_lower = (getattr(incident, "disaster_type", None) or "").strip().lower()
        desc_lower = (getattr(incident, "description", None) or "").strip().lower()
        people = getattr(incident, "people_affected", 0) or 0

        # Determine priority according to priority rules and severity score
        if severity_score >= 70 or any(k in desc_lower for k in ["collapse", "collapsed", "dead", "unconscious", "trapped"]):
            priority = "CRITICAL"
        elif severity_score >= 45 or people >= 20:
            priority = "HIGH"
        elif severity_score >= 20:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        # Determine resources based on disaster type rules
        resources = []
        if disaster_lower == "flood":
            resources = ["Boat", "Rescue Team"]
        elif disaster_lower == "earthquake":
            resources = ["Ambulance", "Rescue Team", "Medical Team"]
        elif disaster_lower == "building collapse":
            resources = ["Excavator", "Rescue Team", "Ambulance", "Medical Team"]
        elif disaster_lower == "fire":
            resources = ["Fire Truck", "Ambulance", "Rescue Team"]
        elif disaster_lower == "cyclone":
            resources = ["Boat", "Ambulance", "Relief Team"]
        elif disaster_lower == "landslide":
            resources = ["Excavator", "Ambulance", "Rescue Team"]
        elif disaster_lower == "medical emergency":
            resources = ["Ambulance", "Medical Team"]
        else:
            resources = ["Rescue Team", "Ambulance"]

        # Additional keyword-based resources
        if any(k in desc_lower for k in ["injured", "bleeding", "medical", "hospital", "unconscious", "casualt"]) and "Ambulance" not in resources:
            resources.append("Ambulance")
        if any(k in desc_lower for k in ["boat", "water", "drown", "stranded", "flooded", "submerged"]) and "Boat" not in resources:
            resources.append("Boat")
        if any(k in desc_lower for k in ["trapped", "collapse", "staircase", "rescue", "under rubble"]) and "Rescue Team" not in resources:
            resources.append("Rescue Team")
        if any(k in desc_lower for k in ["fire", "smoke", "gas leak", "flame", "burn", "explosion"]) and "Fire Truck" not in resources:
            resources.append("Fire Truck")
        if any(k in desc_lower for k in ["debris", "rubble", "excavator", "heavy machinery", "blocked road", "mud"]) and "Excavator" not in resources:
            resources.append("Excavator")

        disaster_name = getattr(incident, "disaster_type", "Emergency") or "Emergency"
        location_name = getattr(incident, "location", "incident location") or "incident location"

        return {
            "priority": priority,
            "resources": resources,
            "reason": (
                f"Automated assessment for {disaster_name} at {location_name} "
                f"(deterministic severity score: {severity_score})."
            ),
        }

    def assess(self, incident):
        """
        Analyze an emergency incident using the local LLM with bounded timeout,
        falling back to deterministic domain assessment if LLM is slow or unavailable.
        """

        prompt = self.prompt_template.format(
            reporter=getattr(incident, "reporter_name", ""),
            disaster=getattr(incident, "disaster_type", ""),
            location=getattr(incident, "location", ""),
            people=getattr(incident, "people_affected", 0),
            description=getattr(incident, "description", ""),
        )

        try:
            response = self.llm.invoke(prompt)

            # LangChain returns AIMessage
            if hasattr(response, "content"):
                response = response.content

            # Extract JSON even if the model adds extra text
            match = re.search(r"\{.*\}", str(response), re.DOTALL)
            if not match:
                raise ValueError("No JSON found in LLM response")

            clean_json = match.group()
            result = json.loads(clean_json)

            priority = result.get("priority")
            if not priority or not isinstance(priority, str):
                priority = "MEDIUM"

            resources = result.get("resources")
            if not isinstance(resources, list) or not resources:
                # If LLM didn't suggest resources, supplement with deterministic resources
                fallback_res = self._deterministic_fallback(incident)
                resources = fallback_res.get("resources", [])

            reason = result.get("reason")
            if not reason or not isinstance(reason, str):
                reason = "AI-generated assessment completed."

            return {
                "priority": priority.upper().strip(),
                "resources": [str(r).strip() for r in resources if str(r).strip()],
                "reason": reason.strip(),
            }

        except Exception as err:
            logger.warning(
                "LLM assessment unavailable, timed out, or returned invalid output: %s. Using deterministic fallback.",
                err,
            )
            return self._deterministic_fallback(incident)