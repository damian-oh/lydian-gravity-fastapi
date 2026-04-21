from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.song_sketch import SongSketch
from app.schemas.song_sketch import SongSketchCreate, SongSketchUpdate


def get_song_sketch(db: Session, song_sketch_id: int) -> SongSketch | None:
    return db.get(SongSketch, song_sketch_id)


def get_song_sketches_by_user(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
) -> list[SongSketch]:
    stmt = (
        select(SongSketch)
        .where(SongSketch.user_id == user_id)
        .order_by(SongSketch.created_at.desc(), SongSketch.id.desc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(stmt).all())


def create_song_sketch(
    db: Session,
    song_sketch_in: SongSketchCreate,
    user_id: int,
) -> SongSketch:
    db_song_sketch = SongSketch(
        **song_sketch_in.model_dump(),
        user_id=user_id,
    )
    db.add(db_song_sketch)
    db.commit()
    db.refresh(db_song_sketch)

    return db_song_sketch


def update_song_sketch(
    db: Session,
    db_song_sketch: SongSketch,
    song_sketch_in: SongSketchUpdate,
) -> SongSketch:
    update_data = song_sketch_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_song_sketch, field, value)

    db.add(db_song_sketch)
    db.commit()
    db.refresh(db_song_sketch)

    return db_song_sketch


def delete_song_sketch(db: Session, db_song_sketch: SongSketch) -> None:
    db.delete(db_song_sketch)
    db.commit()
