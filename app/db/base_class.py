from typing import Any
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    id: Any
    __name__: str

    # Generate __tablename__ automatically from class name (e.g. User -> user)
    @classmethod
    def __declare_last__(cls):
        if not hasattr(cls, "__tablename__"):
            cls.__tablename__ = cls.__name__.lower()