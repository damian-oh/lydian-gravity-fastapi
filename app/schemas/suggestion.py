from pydantic import BaseModel, Field

from app.schemas.chord import ChordBase
from app.schemas.melodic_note import MelodicNoteBase
from app.schemas.song_section import SectionType
from app.services.music_theory import is_valid_mode, is_valid_note
from pydantic import field_validator


class SuggestionChordContext(ChordBase):
    id: int | None = Field(default=None, gt=0)
    section_id: int | None = Field(default=None, gt=0)


class SuggestionMelodicNoteContext(MelodicNoteBase):
    id: int | None = Field(default=None, gt=0)
    section_id: int | None = Field(default=None, gt=0)


class SuggestionSectionContext(BaseModel):
    section_type: SectionType
    label: str | None = Field(default=None, max_length=50)
    order_index: int = Field(ge=0)
    total_beats: int = Field(ge=1, le=512)
    chords: list[SuggestionChordContext] = Field(default_factory=list)
    melodic_notes: list[SuggestionMelodicNoteContext] = Field(default_factory=list)


class NextStepRequest(BaseModel):
    master_tonal_center: str = Field(min_length=1, max_length=10)
    master_mode: str = Field(min_length=1, max_length=20)
    active_section: SuggestionSectionContext
    selected_chord_id: int | None = Field(default=None, gt=0)
    selected_note_id: int | None = Field(default=None, gt=0)

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


class NextStepChordSuggestion(BaseModel):
    id: str
    chord_name: str
    root: str
    quality: str
    notes: list[str]
    parent_mode: str
    reason: str
    tension: str


class NextStepResponse(BaseModel):
    pitch_collection: list[str]
    gravity_center: list[str]
    suggested_chords: list[NextStepChordSuggestion]
    melody_prompt: str
    rhythmic_prompt: str
    interchange_insight: str | None = None
