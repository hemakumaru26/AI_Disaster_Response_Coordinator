import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parents[1] / "disaster.db"

with sqlite3.connect(DATABASE_PATH) as connection:
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM shelters")

    print("Shelters:", cursor.fetchone()[0])

    cursor.execute("SELECT * FROM shelters LIMIT 5")

    for row in cursor.fetchall():
        print(row)
