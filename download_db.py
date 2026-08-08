from __future__ import annotations

import os
import shutil
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "data" / "texas_divorces.sqlite3"
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE.exists():
    print("Database already exists, skipping download.")
    raise SystemExit(0)

if not DATABASE_URL:
    raise SystemExit(
        "DATABASE_URL is not set. Set it to a direct download URL for the SQLite file."
    )

print(f"Downloading database from {DATABASE_URL} ...")
DATABASE.parent.mkdir(parents=True, exist_ok=True)
with urllib.request.urlopen(DATABASE_URL) as response, open(DATABASE, "wb") as out_file:
    shutil.copyfileobj(response, out_file)

print(f"Downloaded database to {DATABASE}")
