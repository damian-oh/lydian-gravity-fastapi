# Lydian Gravity FastAPI

Backend API for **Lydian Gravity**, a full-stack songwriting workspace for
building modal song sketches, saving arrangements, and surfacing harmonic
next-step ideas inspired by modal harmony and George Russell's Lydian Chromatic
Concept.

This repository powers authentication, persistence, and theory suggestion APIs
for the companion Next.js client:
[lydian-gravity-web](https://github.com/damian-oh/lydian-gravity-web).

## Live Demo

| | |
| --- | --- |
| Application | <https://lydiangravity.damianoh.com> |
| API base | <https://api.lydiangravity.damianoh.com/api/v1> |
| Interactive docs | <https://api.lydiangravity.damianoh.com/docs> |

Demo mode is on, so the client can hand a visitor a working account without
registration. The deployment is a showcase, not durable storage: it runs on a
single free-tier instance with an ephemeral filesystem, so saved data resets
when the instance restarts.

## Project Highlights

- **Authenticated songwriting workspace:** Register, log in, update account
  details, and protect every saved sketch behind JWT bearer auth.
- **User-scoped song library:** Store song metadata such as title, tonal center,
  mode, tempo, time signature, and notes for each user.
- **Nested arrangement persistence:** Save complete section arrangements with
  ordered sections, chords, beat positions, durations, and melody notes.
- **Deterministic theory engine:** Generate next-step harmonic suggestions,
  pitch collections, gravity-center cues, melody prompts, rhythmic prompts, and
  modal-interchange insights.
- **Production-minded API shape:** Versioned `/api/v1` routes, typed Pydantic
  schemas, SQLAlchemy models, CORS configuration, health checks, and OpenAPI
  docs.

## Tech Stack

| Layer | Choice |
| --- | --- |
| Runtime | Python 3.13+ |
| API | FastAPI |
| Data | SQLite, SQLAlchemy |
| Auth | JWT bearer tokens, Argon2 password hashing |
| Validation | Pydantic |
| Tooling | uv, pytest, Ruff |

## API Surface

The API is mounted under `/api/v1` by default.

| Area | Routes | Purpose |
| --- | --- | --- |
| Health | `GET /health` | Deployment and uptime check |
| Auth | `POST /auth/register`, `POST /auth/login` | Account creation and token login |
| Users | `GET /users/me`, `PATCH /users/me`, `POST /users/me/password` | Profile and password management |
| Songs | `GET /songs`, `POST /songs`, `GET /songs/{id}`, `PATCH /songs/{id}`, `DELETE /songs/{id}` | User-scoped song library CRUD |
| Arrangements | `PUT /songs/{id}/arrangement` | Replace a saved arrangement with nested sections, chords, and melody notes |
| Suggestions | `POST /suggestions/next-steps` | Return harmonic and melodic next-step guidance for the active section |

OpenAPI documentation is available at `/docs` when the service is running.

## Architecture

```text
app/
|-- main.py                  # FastAPI app, lifespan setup, CORS, routers
|-- api/                     # Dependencies and versioned route registration
|-- api/v1/endpoints/        # auth, health, songs, suggestions, users
|-- core/                    # Settings and security utilities
|-- crud/                    # SQLAlchemy data-access functions
|-- db/                      # Engine/session setup and declarative base
|-- models/                  # SQLAlchemy tables
|-- schemas/                 # Pydantic request/response contracts
`-- services/                # Domain logic for users and music theory
```

The database is intentionally small and explicit: users own song sketches, song
sketches own sections, and sections own chords plus melodic notes. Foreign keys
cascade on delete so removing a user or sketch removes its nested data.

For a deeper look at the persistence model, see
[docs/database-schema.md](docs/database-schema.md).

## Local Development

### Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)

### Install

```bash
uv sync
cp .env.example .env
```

Update `.env` for your local database path, secret key, and frontend origin.
The default local API base path is `/api/v1`.

### Run

```bash
uv run fastapi dev app/main.py
```

Useful local URLs:

- API root: `http://127.0.0.1:8000/`
- Health check: `http://127.0.0.1:8000/api/v1/health`
- OpenAPI docs: `http://127.0.0.1:8000/docs`

## Configuration

The app reads settings from environment variables and, in local development,
from `.env`.

| Variable | Required | Notes |
| --- | --- | --- |
| `PROJECT_NAME` | Yes | API display name used by FastAPI docs |
| `DEBUG` | No | Set to `False` outside local development |
| `API_V1_STR` | No | Defaults to `/api/v1` |
| `DATABASE_URL` | Yes | SQLite URL, for example `sqlite:///./lydian_gravity.db` |
| `SECRET_KEY` | Yes | Generate a unique value with `openssl rand -hex 32` |
| `ALGORITHM` | No | Defaults to `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Defaults to `30` |
| `BACKEND_CORS_ORIGINS` | No | JSON array of allowed frontend origins |
| `DEMO_MODE` | No | Defaults to `False`. Enables throwaway demo sessions |
| `DEMO_SESSION_EXPIRE_MINUTES` | No | Defaults to `720` |
| `DEMO_MAX_SESSIONS_PER_HOUR` | No | Defaults to `60`, counted across all clients |
| `DEMO_MAX_SESSIONS_PER_CLIENT_PER_HOUR` | No | Defaults to `5` |
| `AUTH_LOGIN_MAX_ATTEMPTS_PER_WINDOW` | No | Defaults to `10` per client |
| `AUTH_LOGIN_WINDOW_SECONDS` | No | Defaults to `300` |
| `AUTH_REGISTER_MAX_ATTEMPTS_PER_WINDOW` | No | Defaults to `5` per client |
| `AUTH_REGISTER_WINDOW_SECONDS` | No | Defaults to `3600` |

Example local configuration:

```bash
PROJECT_NAME="Lydian Gravity FastAPI"
DEBUG=True
API_V1_STR="/api/v1"
DATABASE_URL="sqlite:///./lydian_gravity.db"
SECRET_KEY="replace-with-openssl-rand-hex-32"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
BACKEND_CORS_ORIGINS='["http://localhost:3000","http://127.0.0.1:3000"]'
```

## Quality Checks

```bash
uv run pytest
uv run ruff check .
```

The test suite covers authentication, token rejection cases, CORS preflight
behavior, user-scoped song access, nested arrangement saves, input validation,
and deterministic suggestion responses.

## Deployment

The service ships as a container. [`Dockerfile`](Dockerfile) builds it from
`uv.lock`; [`render.yaml`](render.yaml) declares the hosted service, so its
configuration lives in version control rather than in a dashboard. The image is
host-agnostic — the blueprint is the only Render-specific file.

Two constraints carry over to any host:

- **Run exactly one instance.** Rate-limit state is held in process memory and
  the database is SQLite.
- **Keep `--proxy-headers` in the start command.** Per-client ceilings key on
  the client address; behind a proxy without it, every visitor shares one
  bucket.

## Companion Project

The frontend lives in
[lydian-gravity-web](https://github.com/damian-oh/lydian-gravity-web). It
consumes this API for auth, saved libraries, arrangement updates, and theory
suggestions.
