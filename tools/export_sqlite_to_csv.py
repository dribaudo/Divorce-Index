from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

SRC = Path("data/texas_divorces.sqlite3")
OUT = Path("data/divorces_export.csv")

if not SRC.exists():
    raise SystemExit(f"Source DB not found at {SRC}")

conn = sqlite3.connect(SRC)
cur = conn.cursor()

print(f"Exporting rows from {SRC} to {OUT} ...")
with OUT.open("w", newline="", encoding="utf-8") as fh:
    writer = csv.writer(fh)
    # header
    cols = [
        "source_year",
        "petitioner",
        "petitioner_age",
        "respondent",
        "respondent_age",
        "children_under_18",
        "marriage_date",
        "dissolution_date",
        "county_name",
    ]
    writer.writerow(cols)
    q = "SELECT source_year, petitioner, petitioner_age, respondent, respondent_age, children_under_18, marriage_date, dissolution_date, county_name FROM divorces"
    count = 0
    for row in cur.execute(q):
        writer.writerow(row)
        count += 1
        if count % 100000 == 0:
            print(f"Exported {count:,} rows...")

print(f"Export complete: {OUT} ({count:,} rows)")
conn.close()
