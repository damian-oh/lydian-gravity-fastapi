import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chord import Chord
from app.schemas.chord import ChordCreate, ChordUpdate


def get_chord(db: Session, chord_id: int) -> Chord | None:
    return db.get(Chord, chord_id)


def get_chords_by_section(
    db: Session,
    section_id: int,
    skip: int = 0,
    limit: int = 100,
) -> list[Chord]:
    stmt = (
        select(Chord)
        .where(Chord.section_id == section_id)
        .order_by(Chord.order_index.asc(), Chord.id.asc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(stmt).all())


def create_chord(db: Session, chord_in: ChordCreate) -> Chord:
    chord_data = chord_in.model_dump()
    chord_data["notes"] = json.dumps(chord_data["notes"])
    db_chord = Chord(**chord_data)
    db.add(db_chord)
    db.commit()
    db.refresh(db_chord)

    return db_chord


def update_chord(db: Session, db_chord: Chord, chord_in: ChordUpdate) -> Chord:
    update_data = chord_in.model_dump(exclude_unset=True)
    if "notes" in update_data:
        update_data["notes"] = json.dumps(update_data["notes"])

    for field, value in update_data.items():
        setattr(db_chord, field, value)

    db.add(db_chord)
    db.commit()
    db.refresh(db_chord)

    return db_chord


def delete_chord(db: Session, db_chord: Chord) -> None:
    db.delete(db_chord)
    db.commit()
