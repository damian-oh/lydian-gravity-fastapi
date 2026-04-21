from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Chord(Base):
    __tablename__ = "chords"

    # Columns
    id = Column(Integer, primary_key=True, index=True)

    section_id = Column(
        Integer, ForeignKey("song_sections.id", ondelete="CASCADE"), nullable=False
    )

    order_index = Column(Integer, nullable=False)

    root = Column(String(10), nullable=False)

    quality = Column(String(10), nullable=False)

    chord_name = Column(String(30), nullable=False)

    notes = Column(Text, nullable=False)

    start_beat = Column(Float, nullable=False)

    duration_beats = Column(Float, nullable=False)

    parent_mode = Column(String(20), nullable=False)

    # Relationships
    song_section = relationship("SongSection", back_populates="chords")
