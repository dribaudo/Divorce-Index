from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SQLITE = BASE_DIR / "data" / "texas_divorces.sqlite3"
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    elif DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)

    ENGINE = create_engine(DATABASE_URL, future=True, poolclass=NullPool)

    @event.listens_for(ENGINE, "connect")
    def set_postgres_read_only(dbapi_connection, connection_record):
        if "postgresql+psycopg" in DATABASE_URL:
            cursor = dbapi_connection.cursor()
            cursor.execute("SET default_transaction_read_only = on")
            cursor.close()
else:
    sqlite_url = f"sqlite:///{DEFAULT_SQLITE}?mode=ro"
    ENGINE = create_engine(
        sqlite_url,
        future=True,
        poolclass=NullPool,
        connect_args={"check_same_thread": False, "uri": True},
    )

    @event.listens_for(ENGINE, "connect")
    def set_sqlite_read_only(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA query_only = ON")
        cursor.close()


def get_engine() -> Engine:
    return ENGINE
