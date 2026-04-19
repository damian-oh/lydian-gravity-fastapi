import os

import pytest

os.environ["PROJECT_NAME"] = "Lydian Gravity FastAPI Test"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
