from pydantic import BaseModel, ConfigDict, Field


class MelodicNoteBase(BaseModel):
    pitch: int = Field(ge=0, le=127)
    start_beat: float = Field(ge=0)
    duration_beats: float = Field(gt=0)

class MelodicNoteCreate(MelodicNoteBase):
    section_id: int = Field(gt=0)

class MelodicNoteUpdate(BaseModel):
    pitch: int | None = Field(default=None, ge=0, le=127)
    start_beat: float | None = Field(default=None, ge=0)
    duration_beats: float | None = Field(default=None, gt=0)

class MelodicNoteRead(MelodicNoteBase):
    id: int
    section_id: int

    model_config = ConfigDict(from_attributes=True)
