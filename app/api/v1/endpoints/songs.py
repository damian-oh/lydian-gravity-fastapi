import json
import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, SessionDep
from app.crud import crud_song_sketch
from app.services.music_theory import (
    build_chord_notes,
    get_preferred_chromatic,
    is_valid_chord_quality,
    is_valid_note,
)
from app.models.chord import Chord
from app.models.melodic_note import MelodicNote
from app.models.song_section import SongSection
from app.models.song_sketch import SongSketch
from app.schemas.chord import ChordRead
from app.schemas.melodic_note import MelodicNoteRead
from app.schemas.song_sketch import (
    SongArrangementReplace,
    SongRead,
    SongSectionReadNested,
    SongSketchCreate,
    SongSketchRead,
    SongSketchUpdate,
    SongSummaryRead,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_owned_song(db: Session, song_id: int, user_id: int) -> SongSketch:
    song = db.scalar(
        select(SongSketch).where(
            SongSketch.id == song_id,
            SongSketch.user_id == user_id,
        )
    )

    if song is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Song sketch not found.",
        )

    return song


def resolve_chord_notes(chord: Chord, chromatic: tuple[str, ...]) -> list[str] | None:
    """Return the chord's stored notes, repairing or rejecting bad rows.

    The notes column is a denormalized cache of root + quality, so a corrupt
    cell (bad JSON, wrong shape, invalid note names) is recomputed rather than
    allowed to fail ChordRead validation and 500 the whole song. Returns None
    only when root/quality are themselves unusable; callers skip that chord.
    """
    try:
        value = json.loads(chord.notes)
    except (json.JSONDecodeError, TypeError):
        value = None

    if (
        isinstance(value, list)
        and value
        and all(isinstance(note, str) and is_valid_note(note) for note in value)
    ):
        return value

    if is_valid_note(chord.root) and is_valid_chord_quality(chord.quality):
        return list(build_chord_notes(chord.root, chord.quality, chromatic))

    return None


def build_chord_reads(
    section: SongSection, chromatic: tuple[str, ...]
) -> list[ChordRead]:
    reads: list[ChordRead] = []

    for chord in sorted(section.chords, key=lambda item: (item.order_index, item.id)):
        resolved_notes = resolve_chord_notes(chord, chromatic)

        if resolved_notes is not None:
            try:
                reads.append(
                    ChordRead(
                        id=chord.id,
                        section_id=chord.section_id,
                        order_index=chord.order_index,
                        root=chord.root,
                        quality=chord.quality,
                        chord_name=chord.chord_name,
                        notes=resolved_notes,
                        start_beat=chord.start_beat,
                        duration_beats=chord.duration_beats,
                        parent_mode=chord.parent_mode,
                    )
                )
                continue
            except ValidationError:
                pass

        # One corrupt row degrades to a missing chord instead of failing the
        # whole song read.
        logger.warning(
            "Skipping unreadable chord row %s in section %s.",
            chord.id,
            section.id,
        )

    return reads


def build_song_response(song: SongSketch) -> SongRead:
    sections = sorted(
        song.song_sections, key=lambda section: (section.order_index, section.id)
    )
    chromatic = get_preferred_chromatic(song.master_tonal_center, song.master_mode)

    return SongRead(
        id=song.id,
        user_id=song.user_id,
        title=song.title,
        master_tonal_center=song.master_tonal_center,
        master_mode=song.master_mode,
        tempo_bpm=song.tempo_bpm,
        time_signature=song.time_signature,
        notes=song.notes,
        created_at=song.created_at,
        updated_at=song.updated_at,
        sections=[
            SongSectionReadNested(
                id=section.id,
                song_sketch_id=section.song_sketch_id,
                section_type=section.section_type,
                label=section.label,
                order_index=section.order_index,
                total_beats=section.total_beats,
                chords=build_chord_reads(section, chromatic),
                melodic_notes=[
                    MelodicNoteRead.model_validate(note)
                    for note in sorted(
                        section.melodic_notes,
                        key=lambda item: (item.start_beat, item.id),
                    )
                ],
            )
            for section in sections
        ],
    )


@router.get("", response_model=list[SongSummaryRead])
async def read_songs(
    db: SessionDep,
    current_user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[SongSummaryRead]:
    songs = crud_song_sketch.get_song_sketches_by_user(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )

    return [
        SongSummaryRead(
            id=song.id,
            user_id=song.user_id,
            title=song.title,
            master_tonal_center=song.master_tonal_center,
            master_mode=song.master_mode,
            tempo_bpm=song.tempo_bpm,
            time_signature=song.time_signature,
            notes=song.notes,
            created_at=song.created_at,
            updated_at=song.updated_at,
            section_count=len(song.song_sections),
        )
        for song in songs
    ]


@router.post("", response_model=SongRead, status_code=status.HTTP_201_CREATED)
async def create_song(
    db: SessionDep,
    current_user: CurrentUser,
    song_in: SongSketchCreate,
) -> SongRead:
    song = crud_song_sketch.create_song_sketch(
        db,
        song_in,
        user_id=current_user.id,
    )
    section = SongSection(
        song_sketch_id=song.id,
        section_type="A",
        label="Verse 1",
        order_index=0,
        total_beats=16,
    )
    db.add(section)
    db.commit()
    db.refresh(song)

    return build_song_response(song)


@router.get("/{song_id}", response_model=SongRead)
async def read_song(
    db: SessionDep,
    current_user: CurrentUser,
    song_id: int,
) -> SongRead:
    return build_song_response(get_owned_song(db, song_id, current_user.id))


@router.patch("/{song_id}", response_model=SongSketchRead)
async def update_song(
    db: SessionDep,
    current_user: CurrentUser,
    song_id: int,
    song_in: SongSketchUpdate,
) -> SongSketchRead:
    song = get_owned_song(db, song_id, current_user.id)

    return crud_song_sketch.update_song_sketch(db, song, song_in)


@router.delete("/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_song(
    db: SessionDep,
    current_user: CurrentUser,
    song_id: int,
) -> None:
    song = get_owned_song(db, song_id, current_user.id)
    crud_song_sketch.delete_song_sketch(db, song)


@router.put("/{song_id}/arrangement", response_model=SongRead)
async def replace_song_arrangement(
    db: SessionDep,
    current_user: CurrentUser,
    song_id: int,
    arrangement: SongArrangementReplace,
) -> SongRead:
    song = get_owned_song(db, song_id, current_user.id)
    song.song_sections.clear()
    db.flush()

    for section_in in sorted(arrangement.sections, key=lambda item: item.order_index):
        section = SongSection(
            song_sketch_id=song.id,
            section_type=section_in.section_type,
            label=section_in.label,
            order_index=section_in.order_index,
            total_beats=section_in.total_beats,
        )
        section.chords = [
            Chord(
                order_index=chord_in.order_index,
                root=chord_in.root,
                quality=chord_in.quality,
                chord_name=chord_in.chord_name,
                notes=json.dumps(chord_in.notes),
                start_beat=chord_in.start_beat,
                duration_beats=chord_in.duration_beats,
                parent_mode=chord_in.parent_mode,
            )
            for chord_in in sorted(section_in.chords, key=lambda item: item.order_index)
        ]
        section.melodic_notes = [
            MelodicNote(
                pitch=note_in.pitch,
                start_beat=note_in.start_beat,
                duration_beats=note_in.duration_beats,
            )
            for note_in in sorted(
                section_in.melodic_notes,
                key=lambda item: item.start_beat,
            )
        ]
        song.song_sections.append(section)

    # Only child rows change here, so the column's onupdate would never fire;
    # bump the parent timestamp explicitly.
    song.updated_at = func.now()
    db.add(song)
    db.commit()
    db.refresh(song)

    return build_song_response(song)
