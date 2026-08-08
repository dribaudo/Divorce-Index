from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SQLITE = BASE_DIR / "data" / "texas_divorces.sqlite3"
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    ENGINE = create_engine(DATABASE_URL, future=True, poolclass=NullPool)
else:
    sqlite_url = f"sqlite:///{DEFAULT_SQLITE}"
    ENGINE = create_engine(
        sqlite_url,
        future=True,
        poolclass=NullPool,
        connect_args={"check_same_thread": False},
    )


def get_engine() -> Engine:
    return ENGINE
