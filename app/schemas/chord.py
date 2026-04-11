from pydantic import BaseModel, ConfigDict, Field


class ChordBase(BaseModel):
    order_index: int = Field(ge=0)
    root: str = Field(min_length=1, max_length=10)
    quality: str = Field(min_length=1, max_length=10)
    chord_name: str = Field(min_length=1, max_length=30)
    notes: str = Field(min_length=1)
    start_beat: float = Field(ge=0)
    duration_beats: float = Field(gt=0)
    parent_mode: str = Field(min_length=1, max_length=20)

class ChordCreate(ChordBase):
    section_id: int = Field(gt=0)

class ChordUpdate(BaseModel):
    order_index: int | None = Field(default=None, ge=0)
    root: str | None = Field(default=None, min_length=1, max_length=10)
    quality: str | None = Field(default=None, min_length=1, max_length=10)
    chord_name: str | None = Field(default=None, min_length=1, max_length=30)
    notes: str | None = Field(default=None, min_length=1)
    start_beat: float | None = Field(default=None, ge=0)
    duration_beats: float | None = Field(default=None, gt=0)
    parent_mode: str | None = Field(default=None, min_length=1, max_length=20)

class ChordRead(ChordBase):
    id: int
    section_id: int

    model_config = ConfigDict(from_attributes=True)
