from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.config import settings
from app.main import app
from app.models.user import User
from app.services import demo_service

pytestmark = pytest.mark.anyio


@pytest.fixture
def demo_mode() -> AsyncGenerator[None, None]:
    original = settings.DEMO_MODE
    settings.DEMO_MODE = True
    demo_service.reset_throttle()
    yield
    settings.DEMO_MODE = original
    demo_service.reset_throttle()


@asynccontextmanager
async def client_at(host: str) -> AsyncGenerator[AsyncClient, None]:
    """A second client seen by the app as a different address.

    It shares the get_db override the client fixture installed, so both clients
    talk to the same database.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, client=(host, 1234)),
        base_url="http://test",
    ) as other_client:
        yield other_client


def count_users() -> int:
    with app.state.testing_session_local() as db:
        return db.scalar(select(func.count()).select_from(User))


async def start_demo_session(client: AsyncClient) -> str:
    response = await client.post("/api/v1/auth/demo-session")

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"

    return payload["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_demo_session_is_not_found_when_disabled(client: AsyncClient) -> None:
    assert settings.DEMO_MODE is False

    response = await client.post("/api/v1/auth/demo-session")

    assert response.status_code == 404


async def test_demo_session_returns_usable_token(
    client: AsyncClient, demo_mode: None
) -> None:
    token = await start_demo_session(client)

    response = await client.get("/api/v1/users/me", headers=auth_headers(token))

    assert response.status_code == 200
    user = response.json()
    assert user["email"].startswith(demo_service.DEMO_EMAIL_PREFIX)
    assert user["email"].endswith(f"@{demo_service.DEMO_EMAIL_DOMAIN}")


async def test_demo_session_seeds_one_populated_song(
    client: AsyncClient, demo_mode: None
) -> None:
    token = await start_demo_session(client)

    library = await client.get("/api/v1/songs", headers=auth_headers(token))

    assert library.status_code == 200
    songs = library.json()
    assert len(songs) == 1
    assert songs[0]["title"] == demo_service.DEMO_SONG_TITLE
    assert songs[0]["section_count"] == 1

    detail = await client.get(
        f"/api/v1/songs/{songs[0]['id']}", headers=auth_headers(token)
    )

    assert detail.status_code == 200
    song = detail.json()
    assert len(song["sections"]) == 1

    section = song["sections"][0]
    assert len(section["chords"]) == len(demo_service.DEMO_CHORD_DEGREES)
    assert len(section["melodic_notes"]) == len(demo_service.DEMO_MELODY)

    # Chord notes round-trip through the JSON column, and the chords tile the
    # section end to end.
    for chord in section["chords"]:
        assert isinstance(chord["notes"], list)
        assert len(chord["notes"]) == 4
        assert chord["parent_mode"] == demo_service.DEMO_MODE_NAME

    assert section["chords"][0]["start_beat"] == 0
    last_chord = section["chords"][-1]
    assert (
        last_chord["start_beat"] + last_chord["duration_beats"]
        == demo_service.DEMO_SECTION_BEATS
    )


async def test_demo_sessions_are_isolated_from_each_other(
    client: AsyncClient, demo_mode: None
) -> None:
    first_token = await start_demo_session(client)
    second_token = await start_demo_session(client)

    first_user = await client.get("/api/v1/users/me", headers=auth_headers(first_token))
    second_user = await client.get(
        "/api/v1/users/me", headers=auth_headers(second_token)
    )

    assert first_user.json()["id"] != second_user.json()["id"]

    created = await client.post(
        "/api/v1/songs",
        headers=auth_headers(first_token),
        json={
            "title": "Private To Visitor One",
            "master_tonal_center": "D",
            "master_mode": "dorian",
            "tempo_bpm": 110,
        },
    )
    assert created.status_code == 201
    private_song_id = created.json()["id"]

    second_library = await client.get(
        "/api/v1/songs", headers=auth_headers(second_token)
    )
    titles = [song["title"] for song in second_library.json()]

    assert "Private To Visitor One" not in titles
    assert titles == [demo_service.DEMO_SONG_TITLE]

    leaked = await client.get(
        f"/api/v1/songs/{private_song_id}", headers=auth_headers(second_token)
    )

    assert leaked.status_code == 404


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({}, id="no-header"),
        pytest.param({"Authorization": "Bearer not-a-jwt"}, id="garbage-token"),
    ],
)
async def test_demo_mode_does_not_weaken_token_validation(
    client: AsyncClient, demo_mode: None, headers: dict[str, Any]
) -> None:
    response = await client.get("/api/v1/songs", headers=headers)

    assert response.status_code == 401


async def test_demo_accounts_are_flagged_and_registered_accounts_are_not(
    client: AsyncClient, demo_mode: None
) -> None:
    token = await start_demo_session(client)

    demo_user = await client.get("/api/v1/users/me", headers=auth_headers(token))

    assert demo_user.json()["is_demo"] is True

    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": "real@example.com", "password": "correct-password"},
    )

    assert registered.status_code == 201
    assert registered.json()["is_demo"] is False


async def test_demo_session_is_throttled_globally(
    client: AsyncClient, demo_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "DEMO_MAX_SESSIONS_PER_HOUR", 2)
    monkeypatch.setattr(settings, "DEMO_MAX_SESSIONS_PER_CLIENT_PER_HOUR", 100)

    assert (await client.post("/api/v1/auth/demo-session")).status_code == 200
    assert (await client.post("/api/v1/auth/demo-session")).status_code == 200

    throttled = await client.post("/api/v1/auth/demo-session")

    assert throttled.status_code == 429


async def test_demo_throttle_is_scoped_per_client(
    client: AsyncClient, demo_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "DEMO_MAX_SESSIONS_PER_CLIENT_PER_HOUR", 1)

    assert (await client.post("/api/v1/auth/demo-session")).status_code == 200
    assert (await client.post("/api/v1/auth/demo-session")).status_code == 429

    # One visitor exhausting their own allowance must not close the demo for
    # everyone else.
    async with client_at("203.0.113.9") as other_visitor:
        response = await other_visitor.post("/api/v1/auth/demo-session")

    assert response.status_code == 200


async def test_failed_provisioning_leaves_no_account_and_no_quota_spent(
    client: AsyncClient, demo_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "DEMO_MAX_SESSIONS_PER_CLIENT_PER_HOUR", 1)
    original_seed = demo_service.seed_demo_song

    def failing_seed(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("seeding blew up")

    monkeypatch.setattr(demo_service, "seed_demo_song", failing_seed)

    with pytest.raises(RuntimeError):
        await client.post("/api/v1/auth/demo-session")

    assert count_users() == 0

    # The failed attempt must not have spent the visitor's single allowance.
    monkeypatch.setattr(demo_service, "seed_demo_song", original_seed)

    assert (await client.post("/api/v1/auth/demo-session")).status_code == 200
    assert count_users() == 1
