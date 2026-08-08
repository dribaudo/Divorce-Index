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

## Deploy with the database

This project does not include the 966MB SQLite database in git. To deploy with the database:

- Host `data/texas_divorces.sqlite3` at a public URL or object storage location.
- Set the `DATABASE_URL` environment variable to that file URL.
- Render will download the database on startup before launching the app.

## Import another year

```bash
python import_year.py /path/to/div2018.txt --year 2018
```

The importer accepts official DSHS ZIP archives as well as TXT files, preserves source field values, and avoids duplicate rows. The database is at `data/texas_divorces.sqlite3`.
