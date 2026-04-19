from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import jwt
import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.crud import crud_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app

pytestmark = pytest.mark.anyio


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


async def register_user(
    client: AsyncClient,
    email: str = "User@example.com",
    password: str = "correct-password",
) -> Response:
    return await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )


async def login_user(
    client: AsyncClient,
    email: str = "user@example.com",
    password: str = "correct-password",
) -> Response:
    return await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_register_stores_argon2_hash(client: AsyncClient) -> None:
    response = await register_user(client)

    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"
    assert "password_hash" not in response.json()

    with app.state.testing_session_local() as db:
        db_user = crud_user.get_user_by_email(db, email="user@example.com")
        assert db_user is not None
        assert db_user.password_hash != "correct-password"
        assert db_user.password_hash.startswith("$argon2")
        assert verify_password("correct-password", db_user.password_hash)


async def test_duplicate_register_returns_conflict(client: AsyncClient) -> None:
    assert (await register_user(client)).status_code == 201

    response = await register_user(client, email="USER@example.com")

    assert response.status_code == 409


async def test_login_with_oauth2_form_returns_bearer_token(
    client: AsyncClient,
) -> None:
    assert (await register_user(client)).status_code == 201

    response = await login_user(client, email="USER@example.com")

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]


async def test_unknown_email_and_wrong_password_return_unauthorized(
    client: AsyncClient,
) -> None:
    assert (await register_user(client)).status_code == 201

    wrong_password_response = await login_user(client, password="wrong-password")
    unknown_email_response = await login_user(client, email="missing@example.com")

    assert wrong_password_response.status_code == 401
    assert unknown_email_response.status_code == 401
    assert wrong_password_response.json()["detail"] == "Incorrect email or password."
    assert unknown_email_response.json()["detail"] == "Incorrect email or password."


async def test_current_user_rejects_missing_malformed_invalid_and_expired_tokens(
    client: AsyncClient,
) -> None:
    missing_response = await client.get("/api/v1/users/me")
    malformed_response = await client.get(
        "/api/v1/users/me",
        headers=auth_headers("not-a-jwt"),
    )
    invalid_token = jwt.encode(
        {
            "sub": "1",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        },
        "different-secret-with-at-least-32-bytes",
        algorithm=settings.ALGORITHM,
    )
    invalid_response = await client.get(
        "/api/v1/users/me",
        headers=auth_headers(invalid_token),
    )
    missing_exp_token = jwt.encode(
        {"sub": "1"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    missing_exp_response = await client.get(
        "/api/v1/users/me",
        headers=auth_headers(missing_exp_token),
    )
    expired_token = create_access_token(subject=1, expires_delta=timedelta(minutes=-1))
    expired_response = await client.get(
        "/api/v1/users/me",
        headers=auth_headers(expired_token),
    )

    assert missing_response.status_code == 401
    assert malformed_response.status_code == 401
    assert invalid_response.status_code == 401
    assert missing_exp_response.status_code == 401
    assert expired_response.status_code == 401


async def test_current_user_returns_authenticated_user(client: AsyncClient) -> None:
    assert (await register_user(client)).status_code == 201
    token = (await login_user(client)).json()["access_token"]

    response = await client.get("/api/v1/users/me", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


async def test_update_current_user_email_normalizes_and_rejects_duplicates(
    client: AsyncClient,
) -> None:
    assert (await register_user(client)).status_code == 201
    assert (await register_user(client, email="other@example.com")).status_code == 201
    token = (await login_user(client)).json()["access_token"]

    update_response = await client.patch(
        "/api/v1/users/me",
        headers=auth_headers(token),
        json={"email": "NewAddress@example.com"},
    )
    duplicate_response = await client.patch(
        "/api/v1/users/me",
        headers=auth_headers(token),
        json={"email": "OTHER@example.com"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["email"] == "newaddress@example.com"
    assert duplicate_response.status_code == 409


async def test_password_change_requires_current_password_and_replaces_old_password(
    client: AsyncClient,
) -> None:
    assert (await register_user(client)).status_code == 201
    token = (await login_user(client)).json()["access_token"]

    wrong_current_response = await client.post(
        "/api/v1/users/me/password",
        headers=auth_headers(token),
        json={
            "current_password": "wrong-password",
            "new_password": "new-password",
        },
    )
    change_response = await client.post(
        "/api/v1/users/me/password",
        headers=auth_headers(token),
        json={
            "current_password": "correct-password",
            "new_password": "new-password",
        },
    )
    old_login_response = await login_user(client, password="correct-password")
    new_login_response = await login_user(client, password="new-password")

    assert wrong_current_response.status_code == 400
    assert change_response.status_code == 200
    assert change_response.json() == {"message": "Password updated successfully."}
    assert old_login_response.status_code == 401
    assert new_login_response.status_code == 200
