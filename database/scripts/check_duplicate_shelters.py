import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "disaster.db"

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

cursor.execute("""
    SELECT
        name,
        COUNT(*)
    FROM shelters
    GROUP BY name
    HAVING COUNT(*) > 1
    ORDER BY name
""")

duplicates = cursor.fetchall()

print("=" * 70)
print("DUPLICATE SHELTER NAME CHECK")
print("=" * 70)

for name, count in duplicates:

    print(f"\n{name} -> {count} records")

    cursor.execute("""
        SELECT
            id,
            name,
            district,
            address,
            latitude,
            longitude,
            capacity,
            contact
        FROM shelters
        WHERE name = ?
        ORDER BY id
    """, (name,))

    rows = cursor.fetchall()

    for row in rows:
        print(
            f"  ID: {row[0]}\n"
            f"  District: {row[2]}\n"
            f"  Address: {row[3]}\n"
            f"  Coordinates: {row[4]}, {row[5]}\n"
            f"  Capacity: {row[6]}\n"
            f"  Contact: {row[7]}"
        )

connection.close()

print("\n" + "=" * 70)
print("CHECK COMPLETE")
print("=" * 70)
