"""Persistent mission state for future orchestration and approval workflows."""

import json
from contextlib import contextmanager

from backend.database.connection import get_connection


MISSION_STATUSES = {
    "CREATED",
    "ASSESSED",
    "PLANNED",
    "AWAITING_APPROVAL",
    "APPROVED",
    "REJECTED",
    "ACTIVE",
    "COMPLETED",
    "REPLANNING",
}
APPROVAL_STATUSES = {"PENDING", "APPROVED", "REJECTED"}


@contextmanager
def _connection_scope(connection=None):
    """Use a test connection when supplied, otherwise the project database."""
    if connection is not None:
        yield connection
        return

    with get_connection() as project_connection:
        yield project_connection


def initialize_mission_storage(connection=None):
    """Create the minimal persistent mission-state table when needed."""
    with _connection_scope(connection) as active_connection:
        active_connection.execute(
            """
            CREATE TABLE IF NOT EXISTS missions (
                mission_id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'CREATED',
                assessment_data TEXT,
                rescue_plan_data TEXT,
                approval_status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (incident_id) REFERENCES incidents(id)
            )
            """
        )
        active_connection.commit()


def _validate_identifier(value, field_name):
    """Require a positive integer database identifier."""
    if not isinstance(value, int) or value < 1:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


def _serialize_structured_data(value, field_name):
    """Serialize optional structured mission data as JSON."""
    if value is None:
        return None
    if not isinstance(value, (dict, list)):
        raise ValueError(f"{field_name} must be a dictionary, list, or None.")
    try:
        return json.dumps(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field_name} must be JSON serializable.") from error


def _deserialize_structured_data(value):
    """Return stored JSON data in its original structured form."""
    return json.loads(value) if value is not None else None


def _mission_from_row(row):
    """Convert a SQLite row to the public mission representation."""
    if row is None:
        return None
    mission = dict(row)
    mission["assessment_data"] = _deserialize_structured_data(
        mission["assessment_data"]
    )
    mission["rescue_plan_data"] = _deserialize_structured_data(
        mission["rescue_plan_data"]
    )
    return mission


def create_mission(
    incident_id,
    assessment_data=None,
    rescue_plan_data=None,
    connection=None,
):
    """Create a mission only when its referenced incident already exists."""
    incident_id = _validate_identifier(incident_id, "incident_id")
    assessment_json = _serialize_structured_data(assessment_data, "assessment_data")
    rescue_plan_json = _serialize_structured_data(
        rescue_plan_data, "rescue_plan_data"
    )

    with _connection_scope(connection) as active_connection:
        initialize_mission_storage(active_connection)
        incident = active_connection.execute(
            "SELECT 1 FROM incidents WHERE id = ?", (incident_id,)
        ).fetchone()
        if incident is None:
            raise ValueError(f"Incident {incident_id} does not exist.")

        cursor = active_connection.execute(
            """
            INSERT INTO missions (incident_id, assessment_data, rescue_plan_data)
            VALUES (?, ?, ?)
            """,
            (incident_id, assessment_json, rescue_plan_json),
        )
        active_connection.commit()
        mission_id = cursor.lastrowid

    return get_mission_by_id(mission_id, connection)


def get_mission_by_id(mission_id, connection=None):
    """Return a mission with decoded structured data, or ``None`` if absent."""
    mission_id = _validate_identifier(mission_id, "mission_id")
    with _connection_scope(connection) as active_connection:
        initialize_mission_storage(active_connection)
        row = active_connection.execute(
            "SELECT * FROM missions WHERE mission_id = ?", (mission_id,)
        ).fetchone()
    return _mission_from_row(row)


def update_mission_status(mission_id, status, connection=None):
    """Update a mission to one explicit lifecycle status."""
    mission_id = _validate_identifier(mission_id, "mission_id")
    if not isinstance(status, str) or status not in MISSION_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(sorted(MISSION_STATUSES))}.")

    with _connection_scope(connection) as active_connection:
        initialize_mission_storage(active_connection)
        cursor = active_connection.execute(
            """
            UPDATE missions
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE mission_id = ?
            """,
            (status, mission_id),
        )
        active_connection.commit()
        if cursor.rowcount != 1:
            return None
    return get_mission_by_id(mission_id, connection)


def update_approval_status(mission_id, approval_status, connection=None):
    """Update a mission approval state without inferring a lifecycle transition."""
    mission_id = _validate_identifier(mission_id, "mission_id")
    if (
        not isinstance(approval_status, str)
        or approval_status not in APPROVAL_STATUSES
    ):
        raise ValueError(
            f"approval_status must be one of: {', '.join(sorted(APPROVAL_STATUSES))}."
        )

    with _connection_scope(connection) as active_connection:
        initialize_mission_storage(active_connection)
        cursor = active_connection.execute(
            """
            UPDATE missions
            SET approval_status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE mission_id = ?
            """,
            (approval_status, mission_id),
        )
        active_connection.commit()
        if cursor.rowcount != 1:
            return None
    return get_mission_by_id(mission_id, connection)


def update_mission_state(
    mission_id,
    assessment_data=None,
    rescue_plan_data=None,
    connection=None,
):
    """Replace supplied assessment and rescue-plan JSON state for one mission."""
    mission_id = _validate_identifier(mission_id, "mission_id")
    fields = []
    parameters = []

    if assessment_data is not None:
        fields.append("assessment_data = ?")
        parameters.append(_serialize_structured_data(assessment_data, "assessment_data"))
    if rescue_plan_data is not None:
        fields.append("rescue_plan_data = ?")
        parameters.append(
            _serialize_structured_data(rescue_plan_data, "rescue_plan_data")
        )
    if not fields:
        raise ValueError("Provide assessment_data or rescue_plan_data to update.")

    fields.append("updated_at = CURRENT_TIMESTAMP")
    parameters.append(mission_id)

    with _connection_scope(connection) as active_connection:
        initialize_mission_storage(active_connection)
        cursor = active_connection.execute(
            f"UPDATE missions SET {', '.join(fields)} WHERE mission_id = ?",
            parameters,
        )
        active_connection.commit()
        if cursor.rowcount != 1:
            return None
    return get_mission_by_id(mission_id, connection)
