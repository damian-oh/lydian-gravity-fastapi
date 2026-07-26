from typing import Any, AsyncGenerator

import pytest
from httpx import AsyncClient

from app.core.config import settings
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


async def test_demo_session_is_throttled(
    client: AsyncClient, demo_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "DEMO_MAX_SESSIONS_PER_HOUR", 2)

    assert (await client.post("/api/v1/auth/demo-session")).status_code == 200
    assert (await client.post("/api/v1/auth/demo-session")).status_code == 200

    throttled = await client.post("/api/v1/auth/demo-session")

    assert throttled.status_code == 429
