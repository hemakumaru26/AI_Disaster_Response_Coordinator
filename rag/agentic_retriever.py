"""Deterministic query refinement over the project's existing RAG retriever."""

from rag.retriever import retrieve_context


class AgenticRAG:
    """Choose at most two retrieval queries without using an LLM."""

    MINIMUM_SCORE = 0.45

    @staticmethod
    def _value(source, key, default=None):
        if isinstance(source, dict):
            return source.get(key, default)
        return getattr(source, key, default)

    @staticmethod
    def _text(value):
        return value.strip() if isinstance(value, str) and value.strip() else None

    def _incident_details(self, incident, assessment):
        """Validate inputs and collect the supported deterministic query fields."""
        if incident is None or not isinstance(assessment, dict):
            raise ValueError("incident and assessment dictionary inputs are required.")

        disaster_type = self._text(self._value(incident, "disaster_type"))
        location = self._text(self._value(incident, "location"))
        description = self._text(self._value(incident, "description"))
        priority = self._text(assessment.get("priority"))
        people_affected = self._value(incident, "people_affected")
        if people_affected is not None and (
            not isinstance(people_affected, int) or people_affected < 1
        ):
            raise ValueError("incident people_affected must be a positive integer when provided.")

        resources = assessment.get("resources", [])
        if not isinstance(resources, list) or not all(
            isinstance(resource, str) for resource in resources
        ):
            raise ValueError("assessment resources must be a list of strings.")
        resources = [resource.strip() for resource in resources if resource.strip()]

        if not any(
            (disaster_type, location, description, priority, people_affected, resources)
        ):
            raise ValueError("incident or assessment must contain retrieval information.")
        return {
            "disaster_type": disaster_type,
            "location": location,
            "description": description,
            "priority": priority,
            "people_affected": people_affected,
            "resources": resources,
        }

    @staticmethod
    def _initial_query(details):
        parts = []
        if details["disaster_type"]:
            parts.append(f"{details['disaster_type']} response")
        if details["location"]:
            parts.append(f"location {details['location']}")
        if details["priority"]:
            parts.append(f"{details['priority']} priority")
        if details["people_affected"]:
            parts.append(f"{details['people_affected']} people affected")
        if details["resources"]:
            parts.append("resources " + ", ".join(details["resources"]))
        if details["description"]:
            parts.append(details["description"])
        return "; ".join(parts)

    @staticmethod
    def _refined_query(details):
        """Focus one retry on response and safety terms, not narrative details."""
        terms = [details["disaster_type"] or "emergency", "response safety"]
        terms.extend(details["resources"])
        terms.extend(["evacuation", "first response"])
        return " ".join(dict.fromkeys(terms))

    def _useful_results(self, results):
        """Keep only well-formed retrieval results meeting the score threshold."""
        if not isinstance(results, list):
            return []
        useful = []
        for result in results:
            if not isinstance(result, dict):
                continue
            content = self._text(result.get("content"))
            source = self._text(result.get("source"))
            score = result.get("score")
            if (
                content
                and source
                and isinstance(score, (int, float))
                and not isinstance(score, bool)
                and score >= self.MINIMUM_SCORE
            ):
                useful.append(
                    {"content": content, "source": source, "score": float(score)}
                )
        return useful

    @staticmethod
    def _quality(results):
        """Compare result sets by strongest result, then number of useful hits."""
        return (max((result["score"] for result in results), default=0.0), len(results))

    @staticmethod
    def _response(query, refined_query, results, attempts, reason):
        sources = list(dict.fromkeys(result["source"] for result in results))
        return {
            "query": query,
            "refined_query": refined_query,
            "results": results,
            "context": "\n\n".join(result["content"] for result in results),
            "sources": sources,
            "retrieval_attempts": attempts,
            "sufficient": bool(results),
            "reason": reason,
        }

    def retrieve_for_incident(self, incident, assessment, top_k=3):
        """Retrieve guidance with one deterministic refinement when needed."""
        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
            raise ValueError("top_k must be a positive integer.")

        details = self._incident_details(incident, assessment)
        query = self._initial_query(details)
        try:
            first_results = self._useful_results(retrieve_context(query, n_results=top_k))
        except RuntimeError as error:
            return self._response(
                query,
                None,
                [],
                1,
                f"Retrieval unavailable: {error}",
            )

        if first_results:
            return self._response(
                query,
                None,
                first_results,
                1,
                "Initial retrieval met the minimum relevance score.",
            )

        refined_query = self._refined_query(details)
        try:
            refined_results = self._useful_results(
                retrieve_context(refined_query, n_results=top_k)
            )
        except RuntimeError as error:
            return self._response(
                query,
                refined_query,
                [],
                2,
                f"Retrieval unavailable after refinement: {error}",
            )

        selected_results = max(
            (first_results, refined_results), key=self._quality
        )
        if not selected_results:
            return self._response(
                query,
                refined_query,
                [],
                2,
                "No retrieval results met the minimum relevance score.",
            )
        return self._response(
            query,
            refined_query,
            selected_results,
            2,
            "Refined retrieval produced the stronger relevant result set.",
        )
