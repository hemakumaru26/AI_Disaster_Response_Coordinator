import sqlite3
from collections import Counter
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "disaster.db"

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

# ---------------------------------------------------------
# Total records
# ---------------------------------------------------------

cursor.execute("SELECT COUNT(*) FROM shelters")
total = cursor.fetchone()[0]

print("=" * 60)
print("SHELTER DATASET AUDIT")
print("=" * 60)

print(f"\nTotal shelters: {total}")

# ---------------------------------------------------------
# District distribution
# ---------------------------------------------------------

cursor.execute("""
    SELECT district, COUNT(*)
    FROM shelters
    GROUP BY district
    ORDER BY district
""")

district_rows = cursor.fetchall()

print("\nDistrict distribution:")
print("-" * 60)

for district, count in district_rows:
    print(f"{district:25} {count}")

# ---------------------------------------------------------
# Missing / empty values
# ---------------------------------------------------------

print("\nMissing values:")
print("-" * 60)

columns = [
    "name",
    "district",
    "address",
    "latitude",
    "longitude",
    "capacity",
    "contact"
]

for column in columns:

    cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM shelters
        WHERE {column} IS NULL
        OR TRIM(CAST({column} AS TEXT)) = ''
        """
    )

    missing = cursor.fetchone()[0]

    print(f"{column:15} {missing}")

# ---------------------------------------------------------
# Invalid capacity
# ---------------------------------------------------------

cursor.execute("""
    SELECT COUNT(*)
    FROM shelters
    WHERE capacity <= 0
""")

invalid_capacity = cursor.fetchone()[0]

print(f"\nInvalid capacity records: {invalid_capacity}")

# ---------------------------------------------------------
# Invalid coordinates
# ---------------------------------------------------------

cursor.execute("""
    SELECT COUNT(*)
    FROM shelters
    WHERE latitude NOT BETWEEN 8.0 AND 13.6
       OR longitude NOT BETWEEN 76.0 AND 80.5
""")

invalid_coordinates = cursor.fetchone()[0]

print(f"Invalid Tamil Nadu coordinates: {invalid_coordinates}")

# ---------------------------------------------------------
# Duplicate names
# ---------------------------------------------------------

cursor.execute("""
    SELECT name, COUNT(*)
    FROM shelters
    GROUP BY name
    HAVING COUNT(*) > 1
    ORDER BY COUNT(*) DESC
""")

duplicates = cursor.fetchall()

print("\nDuplicate names:")
print("-" * 60)

if duplicates:
    for name, count in duplicates:
        print(f"{name} -> {count}")
else:
    print("None")

connection.close()

print("\n" + "=" * 60)
print("AUDIT COMPLETE")
print("=" * 60)
