import sqlite3
from pathlib import Path

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Path to database/disaster.db
DATABASE_PATH = BASE_DIR / "database" / "disaster.db"


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reporter_name TEXT,
        phone TEXT,
        disaster_type TEXT,
        location TEXT,
        people_affected INTEGER,
        description TEXT,
        priority TEXT,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()