from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base

class SongSketch(Base):
    __tablename__ = "song_sketches"

    # Columns
    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    title = Column(
        String(200),
        nullable=False
    )

    master_tonal_center = Column(
        String(10),
        nullable=False
    )

    master_mode = Column(
        String(20),
        nullable=False
    )

    tempo_bpm = Column(
        Integer,
        nullable=False
    )

    time_signature = Column(
        String(10),
        nullable=False,
        default="4/4"
    )

    notes = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    user = relationship(
        "User",
        back_populates="song_sketches"
    )

    song_sections = relationship(
        "SongSection",
        back_populates="song_sketch",
        cascade="all, delete-orphan"
    )
