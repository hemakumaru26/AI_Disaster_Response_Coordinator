"""SQLite storage operations for volunteer availability tracking."""

from contextlib import contextmanager

from backend.database.connection import get_connection


VALID_AVAILABILITY_STATUSES = {"available", "unavailable"}


@contextmanager
def _connection_scope(connection=None):
    """Use a supplied connection for tests or the project's database by default."""
    if connection is not None:
        yield connection
        return

    with get_connection() as project_connection:
        yield project_connection


def initialize_volunteer_storage(connection=None):
    """Create the volunteer table when it does not already exist."""
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
            "SELECT * FROM volunteers WHERE id = ?", (volunteer_id,)
        ).fetchone()
    return dict(row) if row is not None else None


def get_volunteers(connection=None):
    """Return all volunteers, newest first, or an empty list."""
    with _connection_scope(connection) as active_connection:
        initialize_volunteer_storage(active_connection)
        rows = active_connection.execute(
            "SELECT * FROM volunteers ORDER BY id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_available_volunteers(connection=None):
    """Return only volunteers currently marked as available."""
    with _connection_scope(connection) as active_connection:
        initialize_volunteer_storage(active_connection)
        rows = active_connection.execute(
            """
            SELECT * FROM volunteers
            WHERE availability_status = 'available'
            ORDER BY id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]
