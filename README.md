# Lydian Gravity FastAPI

FastAPI backend for Lydian Gravity, a songwriting assistant that generates harmonic suggestions based on Modal Harmony and George Russell's Lydian Chromatic Concept.

## Tech Stack

- **Runtime:** Python 3.13+
- **API:** FastAPI
- **Database:** SQLite via SQLAlchemy
- **Package manager:** uv
- **Frontend:** Next.js app in a separate repository

## Project Structure

```text
app/
├── main.py                  # FastAPI application entry point
├── api/v1/
│   ├── api.py               # v1 router configuration
│   └── endpoints/           # auth, health, songs, suggestions, users
├── core/                    # Settings and security utilities
├── crud/                    # Data access logic
├── db/                      # Database setup
├── models/                  # SQLAlchemy models
├── schemas/                 # Pydantic schemas
└── services/                # Domain logic
```

## Documentation

- [Database schema](docs/database-schema.md)
- OpenAPI docs are available at `/docs` when the app is running.

## Local Development

### Prerequisites

- Python 3.13+
- uv

### Install

```bash
uv sync
cp .env.example .env
```

Update `.env` for your local database and frontend origin. The default development API base path is `/api/v1`.

### Run

```bash
uv run fastapi dev app/main.py
```

The local API will be available at:

- Root: `http://127.0.0.1:8000/`
- Health check: `http://127.0.0.1:8000/api/v1/health`
- OpenAPI docs: `http://127.0.0.1:8000/docs`

### Verify

```bash
uv run pytest
uv run ruff check .
```

## Configuration

The app reads settings from environment variables and, for local development, from `.env`.

| Variable | Required | Production guidance |
| --- | --- | --- |
| `PROJECT_NAME` | Yes | Human-readable API name. |
| `DEBUG` | No | Set to `False` in production. |
| `API_V1_STR` | No | Defaults to `/api/v1`; keep stable for deployed clients. |
| `DATABASE_URL` | Yes | Use a SQLite URL pointing at persistent storage, for example `sqlite:////data/lydian_gravity.db`. |
| `SECRET_KEY` | Yes | Generate a unique secret with `openssl rand -hex 32`; never reuse the example value. |
| `ALGORITHM` | No | Defaults to `HS256`; keep aligned with issued JWTs. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Defaults to `30`; adjust to your auth policy. |
| `BACKEND_CORS_ORIGINS` | No | JSON array of exact allowed frontend origins, for example `["https://app.example.com"]`. |

Example production environment:

```bash
PROJECT_NAME="Lydian Gravity FastAPI"
DEBUG=False
API_V1_STR="/api/v1"
DATABASE_URL="sqlite:////data/lydian_gravity.db"
SECRET_KEY="<output-of-openssl-rand-hex-32>"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
BACKEND_CORS_ORIGINS='["https://app.example.com"]'
```

## Deployment

This repository does not include platform-specific deployment files. Deploy it as a Python ASGI service on a VPS or PaaS that supports Python 3.13 and persistent disk storage.

### Build Command

```bash
uv sync --locked --no-dev
```

### Start Command

```bash
uv run fastapi run app/main.py --host 0.0.0.0 --port ${PORT:-8000}
```

Most PaaS providers inject `PORT`. On a VPS, set `PORT` yourself or replace `${PORT:-8000}` with the port exposed by your process manager.

### Persistent Database

SQLite tables are created automatically on application startup with `Base.metadata.create_all()`. The database file must be stored on persistent disk. Do not place the production database in an ephemeral deploy directory unless data loss is acceptable.

Recommended production pattern:

1. Mount persistent storage, for example `/data`.
2. Set `DATABASE_URL="sqlite:////data/lydian_gravity.db"`.
3. Back up the SQLite file regularly.

Local `.env` files and SQLite database files are intentionally ignored by git.

### CORS

Set `BACKEND_CORS_ORIGINS` to the exact deployed frontend origins. Include scheme, host, and port when applicable.

```bash
BACKEND_CORS_ORIGINS='["https://app.example.com","https://www.example.com"]'
```

## Deployment Smoke Checks

After deploy, verify the process and routing:

```bash
curl https://api.example.com/
curl https://api.example.com/api/v1/health
```

Expected health response:

```json
{"status":"ok"}
```

Then confirm browser-based clients can authenticate and save songs from the configured frontend origin. If frontend requests fail before reaching the API, recheck `BACKEND_CORS_ORIGINS`.
