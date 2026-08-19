import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
CSV_FILE = BASE_DIR / "datasets" / "shelters.csv"
DATABASE_PATH = BASE_DIR / "disaster.db"

df = pd.read_csv(CSV_FILE, dtype={"contact": "string"})
# A fresh dataset load is a valid initialized state for occupancy tracking.
df["occupancy"] = 0

with sqlite3.connect(DATABASE_PATH) as connection:
    df.to_sql(
        "shelters",
        connection,
        if_exists="replace",
        index=False,
    )

print(f"Loaded {len(df)} shelters successfully.")
