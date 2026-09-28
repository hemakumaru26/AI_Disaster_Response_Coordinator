import os
import sqlite3
from pathlib import Path

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
OVERRIDE_FILE = BASE_DIR / "scratch" / "db_override.txt"


DEFAULT_DB = BASE_DIR / "database" / "disaster.db"
DATABASE_PATH = DEFAULT_DB


def get_database_path():
    if OVERRIDE_FILE.exists():
        try:
            target = OVERRIDE_FILE.read_text(encoding="utf-8").strip()
            if target and Path(target).exists():
                return Path(target)
        except Exception:
            pass
    if str(DATABASE_PATH) != str(DEFAULT_DB):
        return Path(DATABASE_PATH)
    return DEFAULT_DB


def get_connection():
    conn = sqlite3.connect(get_database_path())
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
    severity_score INTEGER,

    resources TEXT,

    status TEXT
)
""")

    conn.commit()
    conn.close()