from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.song_section import SongSection
from app.schemas.song_section import SongSectionCreate, SongSectionUpdate


def get_song_section(db: Session, song_section_id: int) -> SongSection | None:
    return db.get(SongSection, song_section_id)


def get_song_sections_by_song_sketch(
    db: Session,
    song_sketch_id: int,
    skip: int = 0,
    limit: int = 100,
) -> list[SongSection]:
    stmt = (
        select(SongSection)
        .where(SongSection.song_sketch_id == song_sketch_id)
        .order_by(SongSection.order_index.asc(), SongSection.id.asc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(stmt).all())


def create_song_section(db: Session, song_section_in: SongSectionCreate) -> SongSection:
    db_song_section = SongSection(**song_section_in.model_dump())
    db.add(db_song_section)
    db.commit()
    db.refresh(db_song_section)

    return db_song_section


def update_song_section(
    db: Session,
    db_song_section: SongSection,
    song_section_in: SongSectionUpdate,
) -> SongSection:
    update_data = song_section_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_song_section, field, value)

    db.add(db_song_section)
    db.commit()
    db.refresh(db_song_section)

    return db_song_section


def delete_song_section(db: Session, db_song_section: SongSection) -> None:
    db.delete(db_song_section)
    db.commit()
