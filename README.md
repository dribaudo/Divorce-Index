# Texas Divorce Database — 1968–2017

A local Flask search interface backed by SQLite. The included database contains 4,062,866 Texas divorce-index records from 1968–2017. The original 2017 source file is included in `source_data/div2017.txt` for provenance and re-importing.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run
```

Open the local address printed by Flask.

Enter a name keyword to search the **Petitioner** and **Respondent** name fields. Optionally limit the results by year or county. You can also leave the name keyword blank and select a year and/or county to browse that subset. No records appear until you provide one of those search limits.

## Deploy with a managed database

This project can now run against a managed SQL database instead of a local SQLite file.

### Recommended workflow

1. Create a managed database service:
   - Render Postgres
   - ElephantSQL
   - Supabase
   - Railway Postgres
2. Set the managed database URL in Render as `DATABASE_URL`.
3. Deploy the app with the database connection.

### Migrate local data to the managed database

Run this locally after setting `DATABASE_URL` to your managed DB connection string:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="<your-managed-db-url>"
python migrate_to_managed.py
```

This copies the current local SQLite `data/texas_divorces.sqlite3` data into the managed database and creates indexes used by the app.

### Render service settings

- `Build Command`: `pip install -r requirements.txt`
- `Start Command`: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 1 --timeout 120`
- `Environment Variables`:
  - `DATABASE_URL=<your-managed-db-url>`

### Notes

- The app now connects to `DATABASE_URL` first. If unset, it still falls back to local `data/texas_divorces.sqlite3`.
- Keep `DATABASE_FILENAME` only if your local fallback file name differs from `texas_divorces.sqlite3`.

## Import another year

```bash
python import_year.py /path/to/div2018.txt --year 2018
```

The importer accepts official DSHS ZIP archives as well as TXT files, preserves source field values, and avoids duplicate rows. The database is at `data/texas_divorces.sqlite3`.
