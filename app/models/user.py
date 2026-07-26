from sqlalchemy import Boolean, Column, Integer, String, DateTime, text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class User(Base):
    __tablename__ = "users"

    # Columns
    id = Column(Integer, primary_key=True, index=True)

    email = Column(String(255), unique=True, index=True, nullable=False)

    password_hash = Column(String(255), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Marks a throwaway account minted by demo mode. Kept on the row rather than
    # inferred from the email so renaming the account cannot hide it from the
    # purge script, and so the client can label the session accurately.
    is_demo = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )

    # Relationships
    song_sketches = relationship(
        "SongSketch", back_populates="user", cascade="all, delete-orphan"
    )
