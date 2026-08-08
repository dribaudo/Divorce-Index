# Deployment files for Texas Divorce Database

These files are intended to be copied into the root of the current project.

## What they do

- `requirements.txt` adds Gunicorn for production.
- `render.yaml` tells Render how to build and start the Flask app.
- `Procfile` is a backup start command.
- `.gitattributes` tells Git LFS to store the SQLite database as a large file.
- `.gitignore` excludes local Python/environment files.

## Important: keep the database

Do NOT delete or replace:

`data/texas_divorces.sqlite3`

The database is large, so it must be uploaded with Git LFS rather than through the GitHub web interface.

## Local Git setup

After copying these files into the project:

```bash
git init
git branch -M main
git lfs install
git lfs track "data/texas_divorces.sqlite3"
git add .
git commit -m "Prepare app for Render"
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

If the repository was already initialized, do not run `git init` again. Use the existing repository.

GitHub Free currently includes 10 GiB of Git LFS storage and 10 GiB/month of LFS bandwidth. The database is below the 2 GiB per-file Git LFS limit.

## Render

Connect the GitHub repository to Render and create a Web Service. The included `render.yaml` can supply the build/start settings. The service uses:

Build:
`pip install -r requirements.txt`

Start:
`gunicorn app:app`

The SQLite database is read from the project's `data/` directory.
