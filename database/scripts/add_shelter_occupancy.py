"""Add and initialize shelter occupancy tracking safely."""

import sqlite3
from pathlib import Path


DATABASE_PATH = Path(__file__).resolve().parents[1] / "disaster.db"


def add_shelter_occupancy():
    """Create the occupancy column if needed and repair invalid values.

    The migration is idempotent: it can be run repeatedly without trying to
    add the same column more than once.
    """
    with sqlite3.connect(DATABASE_PATH) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(shelters)")
        }

        if "occupancy" not in columns:
            connection.execute(
                "ALTER TABLE shelters ADD COLUMN occupancy INTEGER DEFAULT 0"
            )
            print("Added occupancy column to shelters.")
        else:
            print("Occupancy column already exists.")

        # Existing and future data must obey 0 <= occupancy <= capacity.
        connection.execute(
            """
            UPDATE shelters
            SET occupancy = CASE
                WHEN occupancy IS NULL OR occupancy < 0 THEN 0
                WHEN occupancy > capacity THEN capacity
                ELSE occupancy
            END
            """
        )
        shelter_count = connection.execute(
            "SELECT COUNT(*) FROM shelters"
        ).fetchone()[0]

    print(f"Occupancy initialized for {shelter_count} shelters.")


if __name__ == "__main__":
    add_shelter_occupancy()
