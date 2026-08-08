from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from flask import Flask, g, render_template, request

BASE_DIR = Path(__file__).resolve().parent
DATABASE_FILENAME = os.environ.get("DATABASE_FILENAME", "texas_divorces.sqlite3")
DATABASE = BASE_DIR / "data" / DATABASE_FILENAME
PAGE_SIZE = 50

app = Flask(__name__)


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
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

    clauses, params = [], []
    if query:
        pattern = f"%{query}%"
        clauses.append("(petitioner LIKE ? OR respondent LIKE ?)")
        params.extend([pattern, pattern])
    if county:
        clauses.append("county_name = ?")
        params.append(county)
    if year:
        clauses.append("source_year = ?")
        params.append(year)
    searched = bool(clauses)
    where = f" WHERE {' AND '.join(clauses)}" if searched else ""

    db = get_db()
    total = 0
    rows = []
    if searched:
        total = db.execute(f"SELECT COUNT(*) FROM divorces{where}", params).fetchone()[0]
        rows = db.execute(
            f"SELECT petitioner, petitioner_age, respondent, respondent_age, children_under_18, marriage_date, dissolution_date, county_name FROM divorces{where} ORDER BY dissolution_date, file_number LIMIT ? OFFSET ?",
            [*params, PAGE_SIZE, (page - 1) * PAGE_SIZE],
        ).fetchall()
    counties = db.execute("SELECT DISTINCT county_name FROM divorces WHERE county_name <> '' ORDER BY county_name").fetchall()
    years = db.execute("SELECT DISTINCT source_year FROM divorces ORDER BY source_year DESC").fetchall()
    return render_template("index.html", rows=rows, counties=counties, total=total, page=page,
                           page_size=PAGE_SIZE, query=query, county=county, year=year,
                           years=years, searched=searched)


if __name__ == "__main__":
    app.run(debug=True)
