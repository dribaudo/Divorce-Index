from __future__ import annotations

import os
import psycopg2
from pathlib import Path

CSV = Path("data/divorces_export.csv")
if not CSV.exists():
    raise SystemExit(f"CSV file not found at {CSV}. Run export first.")

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("Set DATABASE_URL in environment to your Neon connection string.")

print(f"Connecting to {DATABASE_URL.split('@')[-1][:60]}...")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print("Creating target table if needed...")
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS divorces (
        source_year TEXT,
        petitioner TEXT,
        petitioner_age TEXT,
        respondent TEXT,
        respondent_age TEXT,
        children_under_18 TEXT,
        marriage_date TEXT,
        dissolution_date TEXT,
        county_name TEXT
    )
    """
)
conn.commit()

print(f"Importing CSV {CSV} via COPY ...")
with CSV.open("r", encoding="utf-8") as fh:
    cur.copy_expert("COPY divorces (source_year, petitioner, petitioner_age, respondent, respondent_age, children_under_18, marriage_date, dissolution_date, county_name) FROM STDIN WITH CSV HEADER", fh)
    conn.commit()

print("Import complete.")
cur.close()
conn.close()
