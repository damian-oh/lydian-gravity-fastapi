from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.v1.api import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine


def ensure_sqlite_schema_compatibility() -> None:
    inspector = inspect(engine)

    if "song_sections" not in inspector.get_table_names():
        return

    section_columns = {column["name"] for column in inspector.get_columns("song_sections")}
    if "total_beats" not in section_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE song_sections ADD COLUMN total_beats INTEGER NOT NULL DEFAULT 16")
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema_compatibility()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {
        "message": "Lydian Gravity FastAPI is online",
        "project": settings.PROJECT_NAME,
    }
