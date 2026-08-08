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
    conn.execute(text(
        """
        CREATE TABLE IF NOT EXISTS divorces (
            source_year TEXT,
            file_number TEXT,
            petitioner TEXT,
            petitioner_age TEXT,
            respondent TEXT,
            respondent_age TEXT,
            children_under_18 TEXT,
            marriage_date TEXT,
            dissolution_date TEXT,
            county_code TEXT,
            county_name TEXT
        )
        """
    ))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_divorces_year ON divorces(source_year)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_divorces_county ON divorces(county_name)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_divorces_petitioner ON divorces(petitioner)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_divorces_respondent ON divorces(respondent)"))

    src_conn = sqlite3.connect(SOURCE_DB)
    src_cur = src_conn.cursor()

    print("Counting rows in source database...")
    total = src_cur.execute("SELECT COUNT(*) FROM divorces").fetchone()[0]
    print(f"Found {total:,} rows to migrate.")

    insert_sql = text(
        "INSERT INTO divorces (source_year, file_number, petitioner, petitioner_age, respondent, respondent_age, children_under_18, marriage_date, dissolution_date, county_code, county_name)"
        " VALUES (:source_year, :file_number, :petitioner, :petitioner_age, :respondent, :respondent_age, :children_under_18, :marriage_date, :dissolution_date, :county_code, :county_name)"
    )

    batch = []
    count = 0
    for row in src_cur.execute(
        "SELECT source_year, file_number, petitioner, petitioner_age, respondent, respondent_age, children_under_18, marriage_date, dissolution_date, county_code, county_name FROM divorces"
    ):
        batch.append({
            "source_year": row[0],
            "file_number": row[1],
            "petitioner": row[2],
            "petitioner_age": row[3],
            "respondent": row[4],
            "respondent_age": row[5],
            "children_under_18": row[6],
            "marriage_date": row[7],
            "dissolution_date": row[8],
            "county_code": row[9],
            "county_name": row[10],
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
