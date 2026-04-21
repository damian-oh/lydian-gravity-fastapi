from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.melodic_note import MelodicNote
from app.schemas.melodic_note import MelodicNoteCreate, MelodicNoteUpdate


def get_melodic_note(db: Session, melodic_note_id: int) -> MelodicNote | None:
    return db.get(MelodicNote, melodic_note_id)


def get_melodic_notes_by_section(
    db: Session,
    section_id: int,
    skip: int = 0,
    limit: int = 100,
) -> list[MelodicNote]:
    stmt = (
        select(MelodicNote)
        .where(MelodicNote.section_id == section_id)
        .order_by(MelodicNote.start_beat.asc(), MelodicNote.id.asc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(stmt).all())


def create_melodic_note(db: Session, melodic_note_in: MelodicNoteCreate) -> MelodicNote:
    db_melodic_note = MelodicNote(**melodic_note_in.model_dump())
    db.add(db_melodic_note)
    db.commit()
    db.refresh(db_melodic_note)

    return db_melodic_note


def update_melodic_note(
    db: Session,
    db_melodic_note: MelodicNote,
    melodic_note_in: MelodicNoteUpdate,
) -> MelodicNote:
    update_data = melodic_note_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_melodic_note, field, value)

    db.add(db_melodic_note)
    db.commit()
    db.refresh(db_melodic_note)

    return db_melodic_note


def delete_melodic_note(db: Session, db_melodic_note: MelodicNote) -> None:
    db.delete(db_melodic_note)
    db.commit()
