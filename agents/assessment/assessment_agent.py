import json
import re
from pathlib import Path

from backend.services.llm_service import get_llm


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

    def assess(self, incident):
        """
        Analyze an emergency incident using the local LLM.
        """

        prompt = self.prompt_template.format(
            reporter=incident.reporter_name,
            disaster=incident.disaster_type,
            location=incident.location,
            people=incident.people_affected,
            description=incident.description
        )

        response = self.llm.invoke(prompt)

        # LangChain returns AIMessage
        if hasattr(response, "content"):
            response = response.content

        try:
            # Extract JSON even if the model adds extra text
            match = re.search(r"\{.*\}", response, re.DOTALL)

            if not match:
                raise ValueError("No JSON found")

            clean_json = match.group()

            result = json.loads(clean_json)

            return {
                "priority": result.get("priority", "MEDIUM"),
                "resources": result.get("resources", []),
                "reason": result.get(
                    "reason",
                    "No explanation provided."
                )
            }

        except Exception:

            # Safe fallback if the LLM returns invalid JSON
            return {
                "priority": "MEDIUM",
                "resources": [],
                "reason": "LLM returned invalid JSON."
            }