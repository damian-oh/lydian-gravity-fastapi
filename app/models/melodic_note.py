from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class MelodicNote(Base):
    __tablename__ = "melodic_notes"

    # Columns
    id = Column(Integer, primary_key=True, index=True)

    section_id = Column(
        Integer, ForeignKey("song_sections.id", ondelete="CASCADE"), nullable=False
    )

    pitch = Column(Integer, nullable=False)

    start_beat = Column(Float, nullable=False)

    duration_beats = Column(Float, nullable=False)

    # Relationships
    song_section = relationship("SongSection", back_populates="melodic_notes")
