from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, g, render_template, request
from sqlalchemy import text

from db import get_engine

BASE_DIR = Path(__file__).resolve().parent
DATABASE_FILENAME = os.environ.get("DATABASE_FILENAME", "texas_divorces.sqlite3")
DATABASE = BASE_DIR / "data" / DATABASE_FILENAME
PAGE_SIZE = 50

app = Flask(__name__)
engine = get_engine()


def get_db():
    if "db" not in g:
        g.db = engine.connect()
    return g.db


@app.teardown_appcontext
def close_db(_error: BaseException | None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.get("/")
def index():
    query = request.args.get("q", "").strip()
    county = request.args.get("county", "").strip()
    year = request.args.get("year", "").strip()
    try:
        page = max(int(request.args.get("page", "1")), 1)
    except ValueError:
        page = 1

    clauses, params = [], {}
    if query:
        pattern = f"%{query.lower()}%"
        clauses.append("(LOWER(petitioner) LIKE :pattern OR LOWER(respondent) LIKE :pattern)")
        params["pattern"] = pattern
    if county:
        clauses.append("county_name = :county")
        params["county"] = county
    if year:
        clauses.append("source_year = :year")
        params["year"] = year
    searched = bool(clauses)
    where = f" WHERE {' AND '.join(clauses)}" if searched else ""

    db = get_db()
    total = 0
    rows = []
    if searched:
        total = int(db.execute(text(f"SELECT COUNT(*) FROM divorces{where}"), params).scalar_one())
        rows = db.execute(
            text(
                f"SELECT petitioner, petitioner_age, respondent, respondent_age, children_under_18, marriage_date, dissolution_date, county_name FROM divorces{where} ORDER BY dissolution_date LIMIT :limit OFFSET :offset"
            ),
            {**params, "limit": PAGE_SIZE, "offset": (page - 1) * PAGE_SIZE},
        ).mappings().all()
    counties = db.execute(text("SELECT DISTINCT county_name FROM divorces WHERE county_name <> '' ORDER BY county_name")).scalars().all()
    years = db.execute(text("SELECT DISTINCT source_year FROM divorces ORDER BY source_year DESC")).scalars().all()
    return render_template("index.html", rows=rows, counties=counties, total=total, page=page,
                           page_size=PAGE_SIZE, query=query, county=county, year=year,
                           years=years, searched=searched)


if __name__ == "__main__":
    app.run(debug=True)
