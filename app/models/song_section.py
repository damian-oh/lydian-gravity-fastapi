from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class SongSection(Base):
    __tablename__ = "song_sections"

    # Columns
    id = Column(Integer, primary_key=True, index=True)

    song_sketch_id = Column(
        Integer, ForeignKey("song_sketches.id", ondelete="CASCADE"), nullable=False
    )

    section_type = Column(String(1), nullable=False)
    label = Column(String(50), nullable=True)
    order_index = Column(Integer, nullable=False)

    total_beats = Column(Integer, nullable=False, default=16)

    # Relationships
    song_sketch = relationship("SongSketch", back_populates="song_sections")

    chords = relationship(
        "Chord", back_populates="song_section", cascade="all, delete-orphan"
    )

    melodic_notes = relationship(
        "MelodicNote", back_populates="song_section", cascade="all, delete-orphan"
    )
