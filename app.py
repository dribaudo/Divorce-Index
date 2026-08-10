from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from flask import Flask, g, render_template, request
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix

from db import get_engine

BASE_DIR = Path(__file__).resolve().parent
DATABASE_FILENAME = os.environ.get("DATABASE_FILENAME", "texas_divorces.sqlite3")
DATABASE = BASE_DIR / "data" / DATABASE_FILENAME
PAGE_SIZE = 50

app = Flask(__name__)
engine = get_engine()

app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", os.urandom(32).hex()),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=True,
    TEMPLATES_AUTO_RELOAD=False,
)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)


def get_db():
    if "db" not in g:
        g.db = engine.connect()
    return g.db


@app.teardown_appcontext
def close_db(_error: BaseException | None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.after_request
def set_security_headers(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; script-src 'none'; frame-ancestors 'none';"
    if request.is_secure:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    return response


@app.get("/")
def index():
    query = request.args.get("q", "").strip()
    if len(query) > 100:
        query = query[:100]
    county = request.args.get("county", "").strip()
    if len(county) > 100:
        county = county[:100]
    year = request.args.get("year", "").strip()
    if len(year) > 10:
        year = year[:10]
    sort = request.args.get("sort", "")
    direction = request.args.get("direction", "asc")
    try:
        page = max(int(request.args.get("page", "1")), 1)
    except ValueError:
        page = 1

    clauses, params = [], {}
    if query:
        combined_field = "LOWER(petitioner || ' ' || respondent)"
        terms = [term[:40] for term in query.lower().split() if term][:10]
        for idx, term in enumerate(terms, start=1):
            pattern = f"%{term}%"
            param_name = f"pattern_{idx}"
            clauses.append(f"{combined_field} LIKE :{param_name}")
            params[param_name] = pattern
    if county:
        clauses.append("county_name = :county")
        params["county"] = county
    if year:
        clauses.append("source_year = :year")
        params["year"] = year
    searched = bool(clauses)
    where = f" WHERE {' AND '.join(clauses)}" if searched else ""

    order_columns = {
        "petitioner": "petitioner",
        "petitioner_age": "petitioner_age",
        "respondent": "respondent",
        "respondent_age": "respondent_age",
        "county": "county_name",
        "marriage_date": "marriage_date",
        "dissolution_date": "dissolution_date",
        "children": "children_under_18",
    }
    sort_column = order_columns.get(sort)
    direction = "desc" if direction == "desc" else "asc"
    order_clause = "ORDER BY dissolution_date DESC"
    if sort_column:
        order_clause = f"ORDER BY {sort_column} {direction.upper()}"

    db = get_db()
    total = 0
    rows = []
    page_options = []
    if searched:
        total = int(db.execute(text(f"SELECT COUNT(*) FROM divorces{where}"), params).scalar_one())
        page_count = (total + PAGE_SIZE - 1) // PAGE_SIZE
        if page_count > 0:
            if page_count <= 100:
                page_options = list(range(1, page_count + 1))
            else:
                visible = {1, 2, 3, 4, 5, page_count - 4, page_count - 3, page_count - 2, page_count - 1, page_count}
                visible.update({page - 2, page - 1, page, page + 1, page + 2})
                page_options = sorted(p for p in visible if 1 <= p <= page_count)
        rows = db.execute(
            text(
                f"SELECT petitioner, petitioner_age, respondent, respondent_age, children_under_18, marriage_date, dissolution_date, county_name FROM divorces{where} {order_clause} LIMIT :limit OFFSET :offset"
            ),
            {**params, "limit": PAGE_SIZE, "offset": (page - 1) * PAGE_SIZE},
        ).mappings().all()
        rows = [dict(row) for row in rows]

        def normalize_date(value: str) -> str:
            if not value:
                return "Unknown"
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d", "%d-%m-%Y"):
                try:
                    parsed = datetime.strptime(value.strip(), fmt)
                    return parsed.strftime("%m/%d/%Y")
                except ValueError:
                    continue
            return "Unknown"

        for row in rows:
            row["marriage_date"] = normalize_date(row["marriage_date"])
            row["dissolution_date"] = normalize_date(row["dissolution_date"])
    counties = db.execute(text("SELECT DISTINCT county_name FROM divorces WHERE county_name <> '' ORDER BY county_name")).scalars().all()
    years = db.execute(text("SELECT DISTINCT source_year FROM divorces ORDER BY source_year DESC")).scalars().all()
    return render_template(
        "index.html",
        rows=rows,
        counties=counties,
        total=total,
        page=page,
        page_size=PAGE_SIZE,
        query=query,
        county=county,
        year=year,
        years=years,
        searched=searched,
        sort=sort,
        direction=direction,
        page_options=page_options,
    )


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=debug_mode)
