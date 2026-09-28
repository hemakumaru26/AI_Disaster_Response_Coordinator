from backend.database.connection import get_connection


def save_incident(
    incident,
    priority,
    severity_score,
    resources
):
    """
    Save a new emergency incident into SQLite.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO incidents
        (
            reporter_name,
            phone,
            disaster_type,
            location,
            people_affected,
            description,
            priority,
            severity_score,
            resources,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        incident.reporter_name,
        incident.phone,
        incident.disaster_type,
        incident.location,
        incident.people_affected,
        incident.description,
        priority,
        severity_score,
        ", ".join(resources),
        "received"
    ))

    conn.commit()

    incident_id = cursor.lastrowid

    conn.close()

    return incident_id


def get_all_incidents():
    """
    Return every incident stored in SQLite.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM incidents
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return [dict(row) for row in rows]


def get_incident_by_id(incident_id, connection=None):
    """Return one incident by id, or None if not found."""
    if not isinstance(incident_id, int) or incident_id < 1:
        raise ValueError("incident_id must be a positive integer.")

    if connection is not None:
        cursor = connection.execute(
            "SELECT * FROM incidents WHERE id = ?", (incident_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        if hasattr(row, "keys"):
            return dict(row)
        columns = [col[0] for col in cursor.description]
        return dict(zip(columns, row))

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
        row = cursor.fetchone()
        return dict(row) if row is not None else None
    finally:
        conn.close()



def get_dashboard_stats():
    """
    Dashboard summary statistics.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM incidents")
    total_incidents = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM incidents
        WHERE priority = 'CRITICAL'
    """)
    critical = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM incidents
        WHERE status = 'received'
    """)
    active = cursor.fetchone()[0]

    conn.close()

    return {
        "total": total_incidents,
        "critical": critical,
        "active": active
    }