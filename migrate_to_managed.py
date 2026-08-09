from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import text

from db import get_engine

SOURCE_DB = Path("data/texas_divorces.sqlite3")
if not SOURCE_DB.exists():
    raise SystemExit("Local source database not found at data/texas_divorces.sqlite3")

engine = get_engine()

print("Connecting to managed database...")
with engine.begin() as conn:
    print("Creating target table if needed...")
    # The local source DB contains these nine columns; create a compatible target table.
    conn.execute(text(
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
    ))
    # Only create the primary search index for this deployment.
    # Additional indexes were skipped due to Neon project size constraints.
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_divorces_petitioner ON divorces(petitioner)"))

    src_conn = sqlite3.connect(SOURCE_DB)
    src_cur = src_conn.cursor()

    print("Counting rows in source database...")
    total = src_cur.execute("SELECT COUNT(*) FROM divorces").fetchone()[0]
    print(f"Found {total:,} rows to migrate.")

    insert_sql = text(
        "INSERT INTO divorces (source_year, petitioner, petitioner_age, respondent, respondent_age, children_under_18, marriage_date, dissolution_date, county_name)"
        " VALUES (:source_year, :petitioner, :petitioner_age, :respondent, :respondent_age, :children_under_18, :marriage_date, :dissolution_date, :county_name)"
    )

    batch = []
    count = 0
    for row in src_cur.execute(
        "SELECT source_year, petitioner, petitioner_age, respondent, respondent_age, children_under_18, marriage_date, dissolution_date, county_name FROM divorces"
    ):
        batch.append({
            "source_year": row[0],
            "petitioner": row[1],
            "petitioner_age": row[2],
            "respondent": row[3],
            "respondent_age": row[4],
            "children_under_18": row[5],
            "marriage_date": row[6],
            "dissolution_date": row[7],
            "county_name": row[8],
        })
        if len(batch) >= 10000:
            conn.execute(insert_sql, batch)
            count += len(batch)
            print(f"Migrated {count:,} rows...")
            batch.clear()

    if batch:
        conn.execute(insert_sql, batch)
        count += len(batch)
        print(f"Migrated {count:,} rows...")

    src_conn.close()

print("Migration complete.")
