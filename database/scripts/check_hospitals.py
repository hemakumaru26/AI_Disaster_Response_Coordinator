import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parents[1] / "disaster.db"

with sqlite3.connect(DATABASE_PATH) as connection:
    rows = connection.execute("SELECT * FROM hospitals").fetchall()

print("Total Hospitals:", len(rows))

for row in rows[:10]:
    print(row)

