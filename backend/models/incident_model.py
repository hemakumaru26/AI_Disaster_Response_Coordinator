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