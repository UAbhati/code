# Notes with live search

FastAPI + vanilla JS notes app. Notes are kept in memory (seeded with dummy data), no database.

## Run
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --reload      # http://localhost:8000
```
`NOTES_SEED_COUNT=100000` sets how many dummy notes are generated (default 20000). Interactive API docs are at `/docs`.

## API
| Method | Path | Notes |
|---|---|---|
| GET | `/api/notes?q=&limit=30&offset=0` | search/list; `limit` max 100 |
| POST | `/api/notes` | `{title, body}` |
| GET | `/api/notes/{id}` | full note |
| PUT | `/api/notes/{id}` | `{title, body}` |
| DELETE | `/api/notes/{id}` | 204 |

## Test and benchmark
```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
.venv/bin/python bench.py
```

See `DECISIONS.md` for the design choices and known limitations.
