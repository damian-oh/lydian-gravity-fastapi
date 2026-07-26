"""Provisioning for demo sessions.

Demo mode does not disable authentication. It mints a real user row and a real
access token, so every ownership query and token check downstream behaves
exactly as it does for a registered account. The only difference is that the
credentials are generated here instead of being chosen by a visitor.
"""

import json
import secrets
import time
from collections import deque
from datetime import timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.crud import crud_song_sketch
from app.models.chord import Chord
from app.models.melodic_note import MelodicNote
from app.models.song_section import SongSection
from app.models.song_sketch import SongSketch
from app.models.user import User
from app.schemas.song_sketch import SongSketchCreate
from app.schemas.token import Token
from app.schemas.user import UserCreate
from app.services import music_theory, user_service

DEMO_EMAIL_DOMAIN = "lydian-gravity.demo"
DEMO_EMAIL_PREFIX = "demo+"

DEMO_SONG_TITLE = "Gravity Demo Sketch"
DEMO_TONAL_CENTER = "C"
DEMO_MODE_NAME = "lydian"
DEMO_TEMPO_BPM = 96
DEMO_SECTION_BEATS = 16

# Scale degrees of the seeded progression (I - II - vi - V in the parent mode).
DEMO_CHORD_DEGREES = (0, 1, 5, 4)

# (pitch, start_beat, duration_beats) -- a short motif over the progression.
# Pitches are MIDI numbers centred on C5 so the melody sits above the chords.
DEMO_MELODY = (
    (72, 0.0, 1.5),
    (74, 1.5, 0.5),
    (76, 2.0, 2.0),
    (78, 4.0, 1.5),
    (76, 5.5, 0.5),
    (74, 6.0, 2.0),
    (81, 8.0, 1.5),
    (79, 9.5, 0.5),
    (76, 10.0, 2.0),
    (74, 12.0, 1.0),
    (72, 13.0, 3.0),
)


class DemoThrottleError(RuntimeError):
    """Raised when demo provisioning exceeds the configured hourly ceiling."""


_recent_provisions: deque[float] = deque()


def _check_throttle() -> None:
    """Cap how many demo accounts can be created per rolling hour.

    Each provision writes a user row, so an unthrottled endpoint is an easy way
    to bloat the database. A single-process in-memory counter is enough for the
    deployment this feature targets.
    """
    now = time.monotonic()
    cutoff = now - 3600

    while _recent_provisions and _recent_provisions[0] < cutoff:
        _recent_provisions.popleft()

    if len(_recent_provisions) >= settings.DEMO_MAX_SESSIONS_PER_HOUR:
        raise DemoThrottleError

    _recent_provisions.append(now)


def reset_throttle() -> None:
    """Clear the throttle window. Used by tests."""
    _recent_provisions.clear()


def create_demo_user(db: Session) -> User:
    """Create a throwaway account reachable only through its access token.

    The password is random and never returned anywhere, so the account cannot
    be logged into through the normal form even though it is a real user row.
    """
    user_in = UserCreate(
        email=f"{DEMO_EMAIL_PREFIX}{uuid4().hex[:12]}@{DEMO_EMAIL_DOMAIN}",
        password=secrets.token_urlsafe(32),
    )

    return user_service.create_user(db, user_in)


def seed_demo_song(db: Session, user_id: int) -> SongSketch:
    """Give a fresh demo account one populated song to open.

    Chords are derived from the theory service rather than hardcoded so the
    seeded progression stays consistent with what the theory panel computes.
    """
    song = crud_song_sketch.create_song_sketch(
        db,
        SongSketchCreate(
            title=DEMO_SONG_TITLE,
            master_tonal_center=DEMO_TONAL_CENTER,
            master_mode=DEMO_MODE_NAME,
            tempo_bpm=DEMO_TEMPO_BPM,
            time_signature="4/4",
            notes="A starter sketch so you have something to play with.",
        ),
        user_id=user_id,
    )

    mode_chords = music_theory.build_mode_seventh_chords(
        DEMO_TONAL_CENTER,
        DEMO_MODE_NAME,
    )
    beats_per_chord = DEMO_SECTION_BEATS / len(DEMO_CHORD_DEGREES)

    section = SongSection(
        section_type="A",
        label="Verse 1",
        order_index=0,
        total_beats=DEMO_SECTION_BEATS,
    )
    section.chords = [
        Chord(
            order_index=order_index,
            root=mode_chords[degree].root,
            quality=mode_chords[degree].quality,
            chord_name=mode_chords[degree].chord_name,
            notes=json.dumps(list(mode_chords[degree].notes)),
            start_beat=order_index * beats_per_chord,
            duration_beats=beats_per_chord,
            parent_mode=DEMO_MODE_NAME,
        )
        for order_index, degree in enumerate(DEMO_CHORD_DEGREES)
    ]
    section.melodic_notes = [
        MelodicNote(pitch=pitch, start_beat=start_beat, duration_beats=duration_beats)
        for pitch, start_beat, duration_beats in DEMO_MELODY
    ]

    song.song_sections.append(section)
    db.add(song)
    db.commit()
    db.refresh(song)

    return song


def provision_demo_session(db: Session) -> Token:
    """Create a seeded demo account and return an access token for it.

    Raises DemoThrottleError when the hourly ceiling is reached.
    """
    _check_throttle()

    user = create_demo_user(db)
    seed_demo_song(db, user_id=user.id)

    access_token = create_access_token(
        subject=user.id,
        expires_delta=timedelta(minutes=settings.DEMO_SESSION_EXPIRE_MINUTES),
    )

    return Token(access_token=access_token, token_type="bearer")
