import json

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, SessionDep
from app.crud import crud_song_sketch
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


def parse_chord_notes(notes: str) -> list[str]:
    try:
        value = json.loads(notes)
    except json.JSONDecodeError:
        return []

    return value if isinstance(value, list) else []


def build_song_response(song: SongSketch) -> SongRead:
    sections = sorted(song.song_sections, key=lambda section: (section.order_index, section.id))

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
                chords=[
                    ChordRead(
                        id=chord.id,
                        section_id=chord.section_id,
                        order_index=chord.order_index,
                        root=chord.root,
                        quality=chord.quality,
                        chord_name=chord.chord_name,
                        notes=parse_chord_notes(chord.notes),
                        start_beat=chord.start_beat,
                        duration_beats=chord.duration_beats,
                        parent_mode=chord.parent_mode,
                    )
                    for chord in sorted(section.chords, key=lambda item: (item.order_index, item.id))
                ],
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
    skip: int = 0,
    limit: int = 100,
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

    db.add(song)
    db.commit()
    db.refresh(song)

    return build_song_response(song)
