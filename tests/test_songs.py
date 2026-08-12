import pytest
from httpx import AsyncClient

from tests.test_auth import auth_headers, login_user, register_user

pytestmark = pytest.mark.anyio


async def create_authenticated_user(
    client: AsyncClient,
    email: str = "songwriter@example.com",
    password: str = "correct-password",
) -> dict[str, str]:
    assert (
        await register_user(client, email=email, password=password)
    ).status_code == 201
    token = (await login_user(client, email=email, password=password)).json()[
        "access_token"
    ]

    return auth_headers(token)


async def create_song(client: AsyncClient, headers: dict[str, str]) -> dict:
    response = await client.post(
        "/api/v1/songs",
        headers=headers,
        json={
            "title": "Sketch One",
            "master_tonal_center": "C",
            "master_mode": "lydian",
            "tempo_bpm": 112,
            "time_signature": "4/4",
            "notes": "Initial notes",
        },
    )

    assert response.status_code == 201

    return response.json()


async def test_song_crud_and_library_summary(client: AsyncClient) -> None:
    headers = await create_authenticated_user(client)
    song = await create_song(client, headers)

    list_response = await client.get("/api/v1/songs", headers=headers)
    read_response = await client.get(f"/api/v1/songs/{song['id']}", headers=headers)
    update_response = await client.patch(
        f"/api/v1/songs/{song['id']}",
        headers=headers,
        json={"title": "Updated Sketch"},
    )
    delete_response = await client.delete(
        f"/api/v1/songs/{song['id']}", headers=headers
    )
    missing_response = await client.get(f"/api/v1/songs/{song['id']}", headers=headers)

    assert list_response.status_code == 200
    assert list_response.json()[0]["section_count"] == 1
    assert read_response.status_code == 200
    assert read_response.json()["sections"][0]["total_beats"] == 16
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated Sketch"
    assert delete_response.status_code == 204
    assert missing_response.status_code == 404


async def test_replace_arrangement_saves_nested_sections_chords_and_notes(
    client: AsyncClient,
) -> None:
    headers = await create_authenticated_user(client)
    song = await create_song(client, headers)

    response = await client.put(
        f"/api/v1/songs/{song['id']}/arrangement",
        headers=headers,
        json={
            "sections": [
                {
                    "section_type": "A",
                    "label": "Verse 1",
                    "order_index": 0,
                    "total_beats": 8,
                    "chords": [
                        {
                            "order_index": 0,
                            "root": "C",
                            "quality": "maj7",
                            "chord_name": "Cmaj7",
                            "notes": ["C", "E", "G", "B"],
                            "start_beat": 0,
                            "duration_beats": 4,
                            "parent_mode": "lydian",
                        }
                    ],
                    "melodic_notes": [
                        {
                            "pitch": 64,
                            "start_beat": 0,
                            "duration_beats": 1,
                        }
                    ],
                },
                {
                    "section_type": "C",
                    "label": "Chorus",
                    "order_index": 1,
                    "total_beats": 4,
                    "chords": [],
                    "melodic_notes": [],
                },
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert [section["label"] for section in body["sections"]] == ["Verse 1", "Chorus"]
    assert body["sections"][0]["chords"][0]["notes"] == ["C", "E", "G", "B"]
    assert body["sections"][0]["melodic_notes"][0]["pitch"] == 64


async def test_song_routes_are_user_scoped(client: AsyncClient) -> None:
    first_headers = await create_authenticated_user(client, email="one@example.com")
    second_headers = await create_authenticated_user(client, email="two@example.com")
    song = await create_song(client, first_headers)

    response = await client.get(f"/api/v1/songs/{song['id']}", headers=second_headers)

    assert response.status_code == 404


async def test_song_validation_rejects_invalid_music_inputs(
    client: AsyncClient,
) -> None:
    headers = await create_authenticated_user(client)
    invalid_song_response = await client.post(
        "/api/v1/songs",
        headers=headers,
        json={
            "title": "Invalid",
            "master_tonal_center": "H",
            "master_mode": "lydian",
            "tempo_bpm": 112,
            "time_signature": "4/4",
        },
    )
    song = await create_song(client, headers)
    invalid_arrangement_response = await client.put(
        f"/api/v1/songs/{song['id']}/arrangement",
        headers=headers,
        json={
            "sections": [
                {
                    "section_type": "A",
                    "label": "Verse",
                    "order_index": 0,
                    "total_beats": 4,
                    "chords": [
                        {
                            "order_index": 0,
                            "root": "C",
                            "quality": "not-a-quality",
                            "chord_name": "C?",
                            "notes": ["C", "E", "G"],
                            "start_beat": 0,
                            "duration_beats": 4,
                            "parent_mode": "lydian",
                        }
                    ],
                    "melodic_notes": [],
                }
            ]
        },
    )

    assert invalid_song_response.status_code == 422
    assert invalid_arrangement_response.status_code == 422


async def test_next_step_suggestions_are_authenticated_and_deterministic(
    client: AsyncClient,
) -> None:
    headers = await create_authenticated_user(client)

    response = await client.post(
        "/api/v1/suggestions/next-steps",
        headers=headers,
        json={
            "master_tonal_center": "C",
            "master_mode": "lydian",
            "selected_chord_id": 1,
            "active_section": {
                "section_type": "A",
                "label": "Verse",
                "order_index": 0,
                "total_beats": 4,
                "chords": [
                    {
                        "id": 1,
                        "order_index": 0,
                        "root": "C",
                        "quality": "maj7",
                        "chord_name": "Cmaj7",
                        "notes": ["C", "E", "G", "B"],
                        "start_beat": 0,
                        "duration_beats": 4,
                        "parent_mode": "lydian",
                    }
                ],
                "melodic_notes": [],
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pitch_collection"] == ["C", "D", "E", "F#", "G", "A", "B"]
    assert [suggestion["id"] for suggestion in body["suggested_chords"]] == [
        "next-diatonic",
        "secondary-dominant",
        "modal-interchange",
    ]


async def test_next_step_suggestions_anchor_on_the_selected_chord(
    client: AsyncClient,
) -> None:
    headers = await create_authenticated_user(client)

    def chord(chord_id: int, root: str, start_beat: float, order_index: int) -> dict:
        return {
            "id": chord_id,
            "order_index": order_index,
            "root": root,
            "quality": "maj7",
            "chord_name": f"{root}maj7",
            "notes": ["C", "E", "G", "B"],
            "start_beat": start_beat,
            "duration_beats": 4,
            "parent_mode": "ionian",
        }

    async def request_suggestions(selected_chord_id: int | None) -> dict:
        response = await client.post(
            "/api/v1/suggestions/next-steps",
            headers=headers,
            json={
                "master_tonal_center": "C",
                "master_mode": "ionian",
                "selected_chord_id": selected_chord_id,
                "active_section": {
                    "section_type": "A",
                    "label": "Verse",
                    "order_index": 0,
                    "total_beats": 8,
                    "chords": [
                        chord(1, "C", 0, 0),
                        chord(2, "E", 4, 1),
                    ],
                    "melodic_notes": [],
                },
            },
        )
        assert response.status_code == 200

        return response.json()

    # Selecting the first chord anchors on C (degree I), so next is Dm7.
    anchored = await request_suggestions(selected_chord_id=1)
    assert anchored["suggested_chords"][0]["chord_name"] == "Dm7"

    # Without a selection the musically last chord (E, degree III) anchors.
    unanchored = await request_suggestions(selected_chord_id=None)
    assert unanchored["suggested_chords"][0]["chord_name"] == "Fmaj7"


async def test_next_step_suggestions_use_flat_spellings_in_flat_modes(
    client: AsyncClient,
) -> None:
    headers = await create_authenticated_user(client)

    response = await client.post(
        "/api/v1/suggestions/next-steps",
        headers=headers,
        json={
            "master_tonal_center": "C",
            "master_mode": "dorian",
            "selected_chord_id": None,
            "active_section": {
                "section_type": "A",
                "label": "Verse",
                "order_index": 0,
                "total_beats": 4,
                "chords": [],
                "melodic_notes": [],
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pitch_collection"] == ["C", "D", "Eb", "F", "G", "A", "Bb"]
    assert not any(
        "#" in note
        for suggestion in body["suggested_chords"]
        for note in suggestion["notes"]
    )


async def test_song_pagination_params_are_validated(client: AsyncClient) -> None:
    headers = await create_authenticated_user(client)

    for query in ("skip=-1", "limit=-1", "limit=0", "limit=201"):
        response = await client.get(f"/api/v1/songs?{query}", headers=headers)

        assert response.status_code == 422, query


async def test_timestamps_are_serialized_with_utc_offset(client: AsyncClient) -> None:
    headers = await create_authenticated_user(client)
    song = await create_song(client, headers)

    assert song["created_at"].endswith("Z") or song["created_at"].endswith("+00:00")


async def test_arrangement_save_bumps_updated_at(client: AsyncClient) -> None:
    from datetime import datetime, timezone

    from app.main import app
    from app.models.song_sketch import SongSketch

    headers = await create_authenticated_user(client)
    song = await create_song(client, headers)

    backdated = datetime(2020, 1, 1, tzinfo=timezone.utc)
    with app.state.testing_session_local() as db:
        row = db.get(SongSketch, song["id"])
        row.updated_at = backdated
        db.commit()

    response = await client.put(
        f"/api/v1/songs/{song['id']}/arrangement",
        headers=headers,
        json={
            "sections": [
                {
                    "section_type": "A",
                    "label": "Verse 1",
                    "order_index": 0,
                    "total_beats": 8,
                    "chords": [],
                    "melodic_notes": [],
                }
            ]
        },
    )

    assert response.status_code == 200
    updated_at = datetime.fromisoformat(response.json()["updated_at"])
    assert updated_at > backdated


async def test_corrupt_chord_rows_degrade_instead_of_failing_the_song(
    client: AsyncClient,
) -> None:
    from app.main import app
    from app.models.chord import Chord

    headers = await create_authenticated_user(client)
    song = await create_song(client, headers)

    def arrangement_chord(order_index: int, root: str, start_beat: float) -> dict:
        return {
            "order_index": order_index,
            "root": root,
            "quality": "maj7",
            "chord_name": f"{root}maj7",
            "notes": [root, "E", "G", "B"],
            "start_beat": start_beat,
            "duration_beats": 4,
            "parent_mode": "lydian",
        }

    save_response = await client.put(
        f"/api/v1/songs/{song['id']}/arrangement",
        headers=headers,
        json={
            "sections": [
                {
                    "section_type": "A",
                    "label": "Verse 1",
                    "order_index": 0,
                    "total_beats": 8,
                    "chords": [
                        arrangement_chord(0, "C", 0),
                        arrangement_chord(1, "G", 4),
                    ],
                    "melodic_notes": [],
                }
            ]
        },
    )
    assert save_response.status_code == 200

    with app.state.testing_session_local() as db:
        first, second = sorted(
            db.query(Chord).all(), key=lambda chord: chord.order_index
        )
        # Corrupt cache: recomputable from root + quality.
        first.notes = "not-json"
        # Unrecoverable row: root itself is garbage.
        second.root = "?"
        db.commit()

    read_response = await client.get(f"/api/v1/songs/{song['id']}", headers=headers)

    assert read_response.status_code == 200
    chords = read_response.json()["sections"][0]["chords"]
    assert len(chords) == 1
    # C lydian is sharp-side, so Cmaj7 recomputes to its natural spelling.
    assert chords[0]["notes"] == ["C", "E", "G", "B"]
