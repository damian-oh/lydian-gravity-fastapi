# Lydian Gravity - Backend

A FastAPI backend that assists songwriters by generating harmonic suggestions based on Modal Harmony and George Russell's Lydian Chromatic Concept (LCTTO).

## Tech Stack

- **Backend:** FastAPI (Python)
- **Database:** SQLite
- **Frontend:** Next.js (React) - separate repository

## Project Structure

```
app/
├── main.py                  # FastAPI application entry point
├── api/v1/
│   ├── api.py               # v1 router configuration
│   └── endpoints/
│       └── health.py        # Health check endpoint
├── core/                    # Configuration and utilities
├── crud/                    # Data access logic
├── db/                      # Database setup
├── models/                  # SQLAlchemy models
└── schemas/                 # Pydantic schemas
```

## Getting Started

### Prerequisites

- Python 3.13+

### Installation

```bash
uv sync
```

### Run

```bash
uv run fastapi dev app/main.py
```
