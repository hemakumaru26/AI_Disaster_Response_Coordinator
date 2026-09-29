import json
import logging
import re
import time
from pathlib import Path

from backend.services.llm_service import get_llm
from backend.services.scoring_service import calculate_severity

logger = logging.getLogger(__name__)


class AssessmentAgent:

    def __init__(self, llm=None):
        self.llm = llm if llm is not None else get_llm()

        prompt_path = (
            Path(__file__).resolve()
            .parents[2]
            / "prompts"
            / "assessment.txt"
        )

        with open(prompt_path, "r", encoding="utf-8") as file:
            self.prompt_template = file.read()

    @property
    def llm_service(self):
        return self.llm

    @llm_service.setter
    def llm_service(self, val):
        self.llm = val

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
            "source": "Deterministic Fallback",
        }

    def assess(self, incident):
        """
        Analyze an emergency incident using the local LLM with bounded timeout,
        falling back to deterministic domain assessment if LLM is slow or unavailable.
        """
        inc_id = getattr(incident, "id", None) or "NEW"
        disaster_type = getattr(incident, "disaster_type", "Emergency")
        location = getattr(incident, "location", "Tamil Nadu")
        people = getattr(incident, "people_affected", 0)

        logger.info(
            "Assessment started | incident_id=%s | disaster=%s | location=%s | people=%s",
            inc_id, disaster_type, location, people
        )

        prompt = self.prompt_template.format(
            reporter=getattr(incident, "reporter_name", ""),
            disaster=disaster_type,
            location=location,
            people=people,
            description=getattr(incident, "description", ""),
        )

        start_t = time.time()
        try:
            logger.info("Ollama attempted | model=qwen2.5:7b | incident_id=%s", inc_id)
            response = self.llm.invoke(prompt)

            # Handle AIMessage or string
            if hasattr(response, "content"):
                response = response.content

            # Extract JSON even if the model adds markdown codeblocks or extra text
            clean_str = str(response).strip()
            # Strip markdown block formatting if present
            if "```" in clean_str:
                code_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean_str, re.DOTALL)
                if code_match:
                    clean_str = code_match.group(1)

            match = re.search(r"\{.*\}", clean_str, re.DOTALL)
            if not match:
                raise ValueError("No valid JSON found in LLM response")

            result = json.loads(match.group())

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

            elapsed = time.time() - start_t
            logger.info(
                "AI assessment succeeded | source=Local Ollama (qwen2.5:7b) | elapsed=%.2fs | priority=%s | resources=%d",
                elapsed, priority.upper().strip(), len(resources)
            )

            return {
                "priority": priority.upper().strip(),
                "resources": [str(r).strip() for r in resources if str(r).strip()],
                "reason": reason.strip(),
                "source": "Local Ollama (qwen2.5:7b)",
            }

        except Exception as err:
            elapsed = time.time() - start_t
            logger.warning(
                "LLM assessment unavailable, timed out, or returned invalid output after %.2fs (%s: %s). Activating Deterministic Fallback.",
                elapsed, type(err).__name__, err,
            )
            fallback = self._deterministic_fallback(incident)
            fallback["source"] = "Deterministic Fallback"
            return fallback