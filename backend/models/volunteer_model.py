"""SQLite storage operations for volunteer availability tracking."""

import sqlite3
from contextlib import contextmanager

from backend.database.connection import get_connection


VALID_AVAILABILITY_STATUSES = {"available", "unavailable"}


@contextmanager
def _connection_scope(connection=None):
    """Use a supplied connection for tests or the project's database by default."""
    if connection is not None:
        if getattr(connection, "row_factory", None) is None:
            connection.row_factory = sqlite3.Row
        yield connection
        return

    with get_connection() as project_connection:
        yield project_connection


def initialize_volunteer_storage(connection=None):
    """Create volunteer and assignment storage when it does not exist."""
    with _connection_scope(connection) as active_connection:
        active_connection.execute(
            """
            CREATE TABLE IF NOT EXISTS volunteers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT NOT NULL,
                district TEXT NOT NULL,
                skills TEXT NOT NULL DEFAULT '',
                availability_status TEXT NOT NULL DEFAULT 'available'
                    CHECK (availability_status IN ('available', 'unavailable')),
                availability_details TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        active_connection.execute(
            """
            CREATE TABLE IF NOT EXISTS volunteer_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                volunteer_id INTEGER NOT NULL,
                incident_id INTEGER NOT NULL,
                required_skill TEXT,
                assignment_status TEXT NOT NULL DEFAULT 'assigned'
                    CHECK (assignment_status IN ('assigned', 'completed')),
                assigned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                FOREIGN KEY (volunteer_id) REFERENCES volunteers(id)
            )
            """
        )
        active_connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_assignment_per_volunteer
            ON volunteer_assignments(volunteer_id)
            WHERE assignment_status = 'assigned'
            """
        )
        active_connection.commit()


def _required_text(value, field_name):
    """Normalize required text values and reject blank input."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required.")
    return value.strip()


def _optional_text(value):
    """Normalize optional text fields for SQLite storage."""
    return value.strip() if isinstance(value, str) else ""


def add_volunteer(
    name,
    contact,
    district,
    skills="",
    availability_status="available",
    availability_details="",
    connection=None,
):
    """Validate and save one volunteer, returning the created record."""
    name = _required_text(name, "Volunteer name")
    contact = _required_text(contact, "Contact information")
    district = _required_text(district, "District")
    availability_status = _required_text(
        availability_status, "Availability status"
    ).lower()
    if availability_status not in VALID_AVAILABILITY_STATUSES:
        raise ValueError("Availability status must be available or unavailable.")

    with _connection_scope(connection) as active_connection:
        initialize_volunteer_storage(active_connection)
        cursor = active_connection.execute(
            """
            INSERT INTO volunteers (
                name, contact, district, skills, availability_status,
                availability_details
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                contact,
                district,
                _optional_text(skills),
                availability_status,
                _optional_text(availability_details),
            ),
        )
        active_connection.commit()
        volunteer_id = cursor.lastrowid

    return get_volunteer_by_id(volunteer_id, connection)


def get_volunteer_by_id(volunteer_id, connection=None):
    """Return a volunteer record by id, or ``None`` if it is absent."""
    with _connection_scope(connection) as active_connection:
        initialize_volunteer_storage(active_connection)
        row = active_connection.execute(
            """
            SELECT volunteers.*,
                   CASE
                       WHEN EXISTS (
                           SELECT 1
                           FROM volunteer_assignments
                           WHERE volunteer_id = volunteers.id
                             AND assignment_status = 'assigned'
                       ) THEN 'assigned'
                       ELSE availability_status
                   END AS current_status
            FROM volunteers
            WHERE id = ?
            """,
            (volunteer_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def get_volunteers(connection=None):
    """Return all volunteers, newest first, or an empty list."""
    with _connection_scope(connection) as active_connection:
        initialize_volunteer_storage(active_connection)
        rows = active_connection.execute(
            """
            SELECT volunteers.*,
                   CASE
                       WHEN EXISTS (
                           SELECT 1
                           FROM volunteer_assignments
                           WHERE volunteer_id = volunteers.id
                             AND assignment_status = 'assigned'
                       ) THEN 'assigned'
                       ELSE availability_status
                   END AS current_status
            FROM volunteers
            ORDER BY id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_available_volunteers(connection=None):
    """Return only volunteers currently marked as available."""
    with _connection_scope(connection) as active_connection:
        initialize_volunteer_storage(active_connection)
        rows = active_connection.execute(
            """
            SELECT volunteers.*,
                   'available' AS current_status
            FROM volunteers
            WHERE availability_status = 'available'
              AND NOT EXISTS (
                  SELECT 1
                  FROM volunteer_assignments
                  WHERE volunteer_id = volunteers.id
                    AND assignment_status = 'assigned'
              )
            ORDER BY id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def _normalize_required_skills(required_skill):
    """Normalize required skill filter into a list of non-empty strings."""
    if required_skill is None:
        return []
    if isinstance(required_skill, (list, tuple, set)):
        result = []
        for item in required_skill:
            if isinstance(item, str) and item.strip() and item.strip() not in result:
                result.append(item.strip())
        return result
    if isinstance(required_skill, str) and required_skill.strip():
        return [required_skill.strip()]
    return []


def get_suitable_volunteers(
    incident_district,
    required_skill=None,
    limit=None,
    same_district_only=False,
    connection=None,
):
    """Return currently assignable volunteers, preferring the incident district."""
    incident_district = _required_text(incident_district, "Incident district")
    skills_to_match = _normalize_required_skills(required_skill)
    if limit is not None and (not isinstance(limit, int) or limit < 1):
        raise ValueError("limit must be a positive integer when provided.")

    district_filter = ""
    district_params = [incident_district, incident_district, incident_district]
    if same_district_only:
        district_filter = """
          AND (
              LOWER(district) = LOWER(?)
              OR LOWER(?) LIKE '%' || LOWER(district) || '%'
              OR LOWER(district) LIKE '%' || LOWER(?) || '%'
          )
        """

    if not skills_to_match:
        query = f"""
            SELECT volunteers.*,
                   'available' AS current_status
            FROM volunteers
            WHERE LOWER(availability_status) = 'available'
              AND NOT EXISTS (
                  SELECT 1
                  FROM volunteer_assignments
                  WHERE volunteer_id = volunteers.id
                    AND LOWER(assignment_status) = 'assigned'
              )
              {district_filter}
            ORDER BY
                CASE
                    WHEN LOWER(district) = LOWER(?) THEN 0
                    WHEN LOWER(?) LIKE '%' || LOWER(district) || '%' THEN 0
                    WHEN LOWER(district) LIKE '%' || LOWER(?) || '%' THEN 0
                    ELSE 1
                END,
                id
        """
        parameters = (district_params if same_district_only else []) + district_params
    else:
        skill_predicates = " OR ".join(["LOWER(skills) LIKE ?" for _ in skills_to_match])
        skill_order_cases = " ".join([f"WHEN LOWER(skills) LIKE ? THEN {i}" for i, _ in enumerate(skills_to_match)])
        query = f"""
            SELECT volunteers.*,
                   'available' AS current_status
            FROM volunteers
            WHERE LOWER(availability_status) = 'available'
              AND NOT EXISTS (
                  SELECT 1
                  FROM volunteer_assignments
                  WHERE volunteer_id = volunteers.id
                    AND LOWER(assignment_status) = 'assigned'
              )
              {district_filter}
              AND ({skill_predicates})
            ORDER BY
                CASE
                    WHEN LOWER(district) = LOWER(?) THEN 0
                    WHEN LOWER(?) LIKE '%' || LOWER(district) || '%' THEN 0
                    WHEN LOWER(district) LIKE '%' || LOWER(?) || '%' THEN 0
                    ELSE 1
                END,
                CASE
                    {skill_order_cases}
                    ELSE {len(skills_to_match)}
                END,
                id
        """
        parameters = (
            (district_params if same_district_only else [])
            + [f"%{s.lower()}%" for s in skills_to_match]
            + district_params
            + [f"%{s.lower()}%" for s in skills_to_match]
        )

    if limit is not None:
        query += " LIMIT ?"
        parameters.append(limit)

    with _connection_scope(connection) as active_connection:
        initialize_volunteer_storage(active_connection)
        rows = active_connection.execute(query, parameters).fetchall()
    return [dict(row) for row in rows]


def assign_volunteer(
    incident_id,
    incident_district,
    required_skill=None,
    same_district_only=False,
    connection=None,
):
    """Assign the best suitable volunteer to an incident, or return ``None``.

    The immediate transaction and partial unique index ensure a volunteer cannot
    receive more than one active assignment, including across parallel requests.
    """
    if not isinstance(incident_id, int) or incident_id < 1:
        raise ValueError("incident_id must be a positive integer.")
    incident_district = _required_text(incident_district, "Incident district")
    skills_to_match = _normalize_required_skills(required_skill)

    district_filter = ""
    district_params = [incident_district, incident_district, incident_district]
    if same_district_only:
        district_filter = """
          AND (
              LOWER(district) = LOWER(?)
              OR LOWER(?) LIKE '%' || LOWER(district) || '%'
              OR LOWER(district) LIKE '%' || LOWER(?) || '%'
          )
        """

    if not skills_to_match:
        select_query = f"""
            SELECT volunteers.id, volunteers.skills
            FROM volunteers
            WHERE LOWER(availability_status) = 'available'
              AND NOT EXISTS (
                  SELECT 1
                  FROM volunteer_assignments
                  WHERE volunteer_id = volunteers.id
                    AND LOWER(assignment_status) = 'assigned'
              )
              {district_filter}
            ORDER BY
                CASE
                    WHEN LOWER(district) = LOWER(?) THEN 0
                    WHEN LOWER(?) LIKE '%' || LOWER(district) || '%' THEN 0
                    WHEN LOWER(district) LIKE '%' || LOWER(?) || '%' THEN 0
                    ELSE 1
                END,
                id
            LIMIT 1
        """
        parameters = (district_params if same_district_only else []) + district_params
    else:
        skill_predicates = " OR ".join(["LOWER(skills) LIKE ?" for _ in skills_to_match])
        skill_order_cases = " ".join([f"WHEN LOWER(skills) LIKE ? THEN {i}" for i, _ in enumerate(skills_to_match)])
        select_query = f"""
            SELECT volunteers.id, volunteers.skills
            FROM volunteers
            WHERE LOWER(availability_status) = 'available'
              AND NOT EXISTS (
                  SELECT 1
                  FROM volunteer_assignments
                  WHERE volunteer_id = volunteers.id
                    AND LOWER(assignment_status) = 'assigned'
              )
              {district_filter}
              AND ({skill_predicates})
            ORDER BY
                CASE
                    WHEN LOWER(district) = LOWER(?) THEN 0
                    WHEN LOWER(?) LIKE '%' || LOWER(district) || '%' THEN 0
                    WHEN LOWER(district) LIKE '%' || LOWER(?) || '%' THEN 0
                    ELSE 1
                END,
                CASE
                    {skill_order_cases}
                    ELSE {len(skills_to_match)}
                END,
                id
            LIMIT 1
        """
        parameters = (
            (district_params if same_district_only else [])
            + [f"%{s.lower()}%" for s in skills_to_match]
            + district_params
            + [f"%{s.lower()}%" for s in skills_to_match]
        )

    with _connection_scope(connection) as active_connection:
        initialize_volunteer_storage(active_connection)
        active_connection.execute("BEGIN IMMEDIATE")
        try:
            row = active_connection.execute(select_query, parameters).fetchone()
            if row is None:
                active_connection.commit()
                return None

            # Resolve the specific skill this volunteer matched
            matched_skill = None
            if skills_to_match:
                v_skills = (dict(row).get("skills") or "").lower()
                for s in skills_to_match:
                    if s.lower() in v_skills:
                        matched_skill = s
                        break
                if matched_skill is None:
                    matched_skill = skills_to_match[0]

            cursor = active_connection.execute(
                """
                INSERT INTO volunteer_assignments (
                    volunteer_id, incident_id, required_skill
                ) VALUES (?, ?, ?)
                """,
                (row["id"], incident_id, matched_skill),
            )
            active_connection.commit()
        except Exception:
            active_connection.rollback()
            raise

        assignment_id = cursor.lastrowid

    return get_assignment_by_id(assignment_id, connection)


def get_assignment_by_id(assignment_id, connection=None):
    """Return an assignment with its volunteer details, or ``None``."""
    with _connection_scope(connection) as active_connection:
        initialize_volunteer_storage(active_connection)
        row = active_connection.execute(
            """
            SELECT volunteer_assignments.*, volunteers.name AS volunteer_name,
                   volunteers.district AS volunteer_district,
                   volunteers.skills AS volunteer_skills,
                   volunteers.contact AS volunteer_contact
            FROM volunteer_assignments
            JOIN volunteers ON volunteers.id = volunteer_assignments.volunteer_id
            WHERE volunteer_assignments.id = ?
            """,
            (assignment_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def complete_assignment(assignment_id, connection=None):
    """Complete one active assignment and release only its volunteer."""
    if not isinstance(assignment_id, int) or assignment_id < 1:
        raise ValueError("assignment_id must be a positive integer.")

    with _connection_scope(connection) as active_connection:
        initialize_volunteer_storage(active_connection)
        cursor = active_connection.execute(
            """
            UPDATE volunteer_assignments
            SET assignment_status = 'completed',
                completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND assignment_status = 'assigned'
            """,
            (assignment_id,),
        )
        active_connection.commit()
        if cursor.rowcount != 1:
            return None

    return get_assignment_by_id(assignment_id, connection)


def release_incident_volunteers(incident_id, connection=None):
    """Release active volunteer assignments for an incident by deleting them."""
    if not isinstance(incident_id, int) or incident_id < 1:
        raise ValueError("incident_id must be a positive integer.")

    with _connection_scope(connection) as active_connection:
        initialize_volunteer_storage(active_connection)
        cursor = active_connection.execute(
            """
            DELETE FROM volunteer_assignments
            WHERE incident_id = ?
              AND assignment_status = 'assigned'
            """,
            (incident_id,),
        )
        active_connection.commit()
        return cursor.rowcount


def complete_incident_volunteers(incident_id, connection=None):
    """Mark all active volunteer assignments for an incident as completed."""
    if not isinstance(incident_id, int) or incident_id < 1:
        raise ValueError("incident_id must be a positive integer.")

    with _connection_scope(connection) as active_connection:
        initialize_volunteer_storage(active_connection)
        cursor = active_connection.execute(
            """
            UPDATE volunteer_assignments
            SET assignment_status = 'completed',
                completed_at = CURRENT_TIMESTAMP
            WHERE incident_id = ?
              AND assignment_status = 'assigned'
            """,
            (incident_id,),
        )
        active_connection.commit()
        return cursor.rowcount
