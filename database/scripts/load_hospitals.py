import sqlite3
import pandas as pd
from pathlib import Path

# Project root
BASE_DIR = Path(__file__).resolve().parent.parent

CSV_FILE = BASE_DIR / "datasets" / "hospitals.csv"
DB_FILE = BASE_DIR / "disaster.db"

# Load CSV
df = pd.read_csv(CSV_FILE)

# Connect SQLite
connection = sqlite3.connect(DB_FILE)

# Replace existing table
df.to_sql(
    "hospitals",
    connection,
    if_exists="replace",
    index=False
)

connection.commit()
connection.close()

print(f"Loaded {len(df)} hospitals successfully.")
print("Database Updated.")