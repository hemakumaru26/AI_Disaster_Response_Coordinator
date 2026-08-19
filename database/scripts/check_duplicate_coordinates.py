import sqlite3
from difflib import SequenceMatcher
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "disaster.db"


def classify_coordinate_group(rows):
    """Classify shared coordinates without treating every match as an error.

    Different named facilities may intentionally use a shared or approximate
    city/district coordinate. A same-district pair with near-identical names
    is flagged for review rather than silently changed.
    """
    districts = {row[2] for row in rows}
    for index, first in enumerate(rows):
        for second in rows[index + 1:]:
            similarity = SequenceMatcher(
                None, first[1].lower(), second[1].lower()
            ).ratio()
            if first[2] == second[2] and similarity >= 0.85:
                return (
                    "SUSPICIOUS: same-district facilities have very similar "
                    "names; verify source coordinates before changing data."
                )

    if len(districts) > 1:
        return (
            "SHARED/BOUNDARY LOCATION: different district records use the "
            "same coordinate; retained as a possible shared locality."
        )
    return (
        "SHARED/APPROXIMATE LOCATION: distinct named facilities in one "
        "district share a coordinate; retained for source verification."
    )

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

cursor.execute("""
    SELECT
        latitude,
        longitude,
        COUNT(*)
    FROM shelters
    GROUP BY latitude, longitude
    HAVING COUNT(*) > 1
    ORDER BY COUNT(*) DESC
""")

duplicates = cursor.fetchall()

print("=" * 70)
print("DUPLICATE COORDINATE CHECK")
print("=" * 70)

if not duplicates:
    print("\nNo duplicate coordinates found.")

for latitude, longitude, count in duplicates:

    print(
        f"\nCoordinates: {latitude}, {longitude}"
        f" -> {count} records"
    )

    cursor.execute("""
        SELECT
            id,
            name,
            district,
            address,
            capacity
        FROM shelters
        WHERE latitude = ?
        AND longitude = ?
        ORDER BY id
    """, (latitude, longitude))

    rows = cursor.fetchall()

    print(f"  Classification: {classify_coordinate_group(rows)}")

    for row in rows:
        print(
            f"  ID: {row[0]} | "
            f"{row[1]} | "
            f"{row[2]} | "
            f"{row[3]} | "
            f"Capacity: {row[4]}"
        )

connection.close()

print("\n" + "=" * 70)
print("CHECK COMPLETE")
print("=" * 70)
