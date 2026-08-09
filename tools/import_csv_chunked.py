from __future__ import annotations

import os
import csv
import psycopg2
from io import StringIO
from pathlib import Path

CSV = Path("data/divorces_export.csv")
if not CSV.exists():
    raise SystemExit(f"CSV file not found at {CSV}. Run export first.")

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("Set DATABASE_URL in environment to your Neon connection string.")

CHUNK_SIZE = 20_000
CONNECT_TIMEOUT = 10
KEEPALIVES = 1
KEEPALIVES_IDLE = 30
KEEPALIVES_INTERVAL = 10
KEEPALIVES_COUNT = 5

def copy_chunk(cur, rows):
    sio = StringIO()
    writer = csv.writer(sio)
    writer.writerows(rows)
    sio.seek(0)
    cur.copy_expert(
        "COPY divorces (source_year, petitioner, petitioner_age, respondent, respondent_age, children_under_18, marriage_date, dissolution_date, county_name) FROM STDIN WITH CSV",
        sio,
    )

def main():
    print(f"Connecting to {DATABASE_URL.split('@')[-1][:60]}...")
    conn = psycopg2.connect(
        DATABASE_URL,
        connect_timeout=CONNECT_TIMEOUT,
        keepalives=KEEPALIVES,
        keepalives_idle=KEEPALIVES_IDLE,
        keepalives_interval=KEEPALIVES_INTERVAL,
        keepalives_count=KEEPALIVES_COUNT,
    )
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

    total = 0
    chunk = []
    chunk_i = 0
    existing_rows = 0
    print(f"Reading and importing in chunks of {CHUNK_SIZE} rows...")
    with conn.cursor() as count_cur:
        count_cur.execute("SELECT COUNT(*) FROM divorces")
        existing_rows = count_cur.fetchone()[0]
    if existing_rows:
        print(f"Resuming import at row {existing_rows + 1}.")
    with CSV.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        for row_i, row in enumerate(reader, 1):
            if row_i <= existing_rows:
                continue
            chunk.append(row)
            if len(chunk) >= CHUNK_SIZE:
                copy_chunk(cur, chunk)
                conn.commit()
                total += len(chunk)
                chunk_i += 1
                print(f"Imported chunk {chunk_i}: {existing_rows + total:,} rows so far")
                chunk = []
        if chunk:
            copy_chunk(cur, chunk)
            conn.commit()
            total += len(chunk)
            chunk_i += 1
            print(f"Imported final chunk {chunk_i}: total {existing_rows + total:,} rows")

    print("Creating indexes...")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_divorces_petitioner ON divorces (lower(petitioner));")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_divorces_respondent ON divorces (lower(respondent));")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_divorces_year ON divorces (source_year);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_divorces_county ON divorces (county_name);")
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM divorces")
    cnt = cur.fetchone()[0]
    print(f"Import complete. Remote row count: {cnt:,}")

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
