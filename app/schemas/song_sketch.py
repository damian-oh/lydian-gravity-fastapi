from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.chord import ChordBase, ChordRead
from app.schemas.melodic_note import MelodicNoteBase, MelodicNoteRead
from app.schemas.song_section import SongSectionBase, SongSectionRead
from app.services.music_theory import is_valid_mode, is_valid_note


class SongSketchBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    master_tonal_center: str = Field(min_length=1, max_length=10)
    master_mode: str = Field(min_length=1, max_length=20)
    tempo_bpm: int = Field(ge=20, le=300)
    time_signature: str = Field(default="4/4", pattern=r"^\d+/\d+$", max_length=10)
    notes: str | None = None

    @field_validator("master_tonal_center")
    @classmethod
    def validate_master_tonal_center(cls, value: str) -> str:
        if not is_valid_note(value):
            raise ValueError("Master tonal center must be a valid note name.")

        return value

    @field_validator("master_mode")
    @classmethod
    def validate_master_mode(cls, value: str) -> str:
        if not is_valid_mode(value):
            raise ValueError("Master mode must be supported.")

        return value


class SongSketchCreate(SongSketchBase):
    pass


class SongSketchUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    master_tonal_center: str | None = Field(default=None, min_length=1, max_length=10)
    master_mode: str | None = Field(default=None, min_length=1, max_length=20)
    tempo_bpm: int | None = Field(default=None, ge=20, le=300)
    time_signature: str | None = Field(
        default=None,
        pattern=r"^\d+/\d+$",
        max_length=10,
    )
    notes: str | None = None

    @field_validator("master_tonal_center")
    @classmethod
    def validate_optional_master_tonal_center(cls, value: str | None) -> str | None:
        if value is not None and not is_valid_note(value):
            raise ValueError("Master tonal center must be a valid note name.")

        return value

    @field_validator("master_mode")
    @classmethod
    def validate_optional_master_mode(cls, value: str | None) -> str | None:
        if value is not None and not is_valid_mode(value):
            raise ValueError("Master mode must be supported.")

        return value


class SongSketchRead(SongSketchBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SongSummaryRead(SongSketchRead):
    section_count: int = 0


class ChordArrangementWrite(ChordBase):
    id: int | None = Field(default=None, gt=0)


class MelodicNoteArrangementWrite(MelodicNoteBase):
    id: int | None = Field(default=None, gt=0)


class SongSectionArrangementWrite(SongSectionBase):
    id: int | None = Field(default=None, gt=0)
    chords: list[ChordArrangementWrite] = Field(default_factory=list)
    melodic_notes: list[MelodicNoteArrangementWrite] = Field(default_factory=list)


class SongArrangementReplace(BaseModel):
    sections: list[SongSectionArrangementWrite] = Field(min_length=1)


class SongSectionReadNested(SongSectionRead):
    chords: list[ChordRead] = Field(default_factory=list)
    melodic_notes: list[MelodicNoteRead] = Field(default_factory=list)


class SongRead(SongSketchRead):
    sections: list[SongSectionReadNested] = Field(default_factory=list)
