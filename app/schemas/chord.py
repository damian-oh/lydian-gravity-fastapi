import json

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.music_theory import is_valid_chord_quality, is_valid_mode, is_valid_note

class ChordBase(BaseModel):
    order_index: int = Field(ge=0)
    root: str = Field(min_length=1, max_length=10)
    quality: str = Field(min_length=1, max_length=10)
    chord_name: str = Field(min_length=1, max_length=30)
    notes: list[str] = Field(min_length=1)
    start_beat: float = Field(ge=0)
    duration_beats: float = Field(gt=0)
    parent_mode: str = Field(min_length=1, max_length=20)

    @field_validator("root")
    @classmethod
    def validate_root(cls, value: str) -> str:
        if not is_valid_note(value):
            raise ValueError("Chord root must be a valid note name.")

        return value

    @field_validator("quality")
    @classmethod
    def validate_quality(cls, value: str) -> str:
        if not is_valid_chord_quality(value):
            raise ValueError("Chord quality is not supported.")

        return value

    @field_validator("parent_mode")
    @classmethod
    def validate_parent_mode(cls, value: str) -> str:
        if value != "secondary dominant" and not is_valid_mode(value):
            raise ValueError("Parent mode must be supported.")

        return value

    @field_validator("notes", mode="before")
    @classmethod
    def parse_notes(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("Chord notes must be a JSON array.") from None

        return value

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: list[str]) -> list[str]:
        for note in value:
            if not is_valid_note(note):
                raise ValueError("Chord notes must contain valid note names.")

        return value

class ChordCreate(ChordBase):
    section_id: int = Field(gt=0)

class ChordUpdate(BaseModel):
    order_index: int | None = Field(default=None, ge=0)
    root: str | None = Field(default=None, min_length=1, max_length=10)
    quality: str | None = Field(default=None, min_length=1, max_length=10)
    chord_name: str | None = Field(default=None, min_length=1, max_length=30)
    notes: list[str] | None = Field(default=None, min_length=1)
    start_beat: float | None = Field(default=None, ge=0)
    duration_beats: float | None = Field(default=None, gt=0)
    parent_mode: str | None = Field(default=None, min_length=1, max_length=20)

class ChordRead(ChordBase):
    id: int
    section_id: int

    model_config = ConfigDict(from_attributes=True)
