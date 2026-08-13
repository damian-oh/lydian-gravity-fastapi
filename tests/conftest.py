import os
from typing import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["PROJECT_NAME"] = "Lydian Gravity FastAPI Test"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
# Pinned so the suite does not inherit a developer's local .env, where demo mode
# may well be on. Tests that need it enable it explicitly.
os.environ["DEMO_MODE"] = "False"

from app.api.v1.endpoints import auth as auth_endpoints  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def _reset_auth_throttles() -> Generator[None, None, None]:
    """Every test's default client shares one address, so without a reset the
    login/register throttles would accumulate hits across unrelated tests."""
    auth_endpoints.reset_auth_throttles()
    yield
    auth_endpoints.reset_auth_throttles()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)

    async def override_get_db() -> AsyncGenerator[Session, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.state.testing_session_local = TestingSessionLocal

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    del app.state.testing_session_local
    Base.metadata.drop_all(bind=engine)
