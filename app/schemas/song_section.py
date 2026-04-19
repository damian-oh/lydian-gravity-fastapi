from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

SectionType = Literal["A", "B", "C", "D"]

class SongSectionBase(BaseModel):
    section_type: SectionType
    label: str | None = Field(default=None, max_length=50)
    order_index: int = Field(ge=0)
    total_beats: int = Field(default=16, ge=1, le=512)

class SongSectionCreate(SongSectionBase):
    song_sketch_id: int = Field(gt=0)

class SongSectionUpdate(BaseModel):
    section_type: SectionType | None = None
    label: str | None = Field(default=None, max_length=50)
    order_index: int | None = Field(default=None, ge=0)
    total_beats: int | None = Field(default=None, ge=1, le=512)

class SongSectionRead(SongSectionBase):
    id: int
    song_sketch_id: int

    model_config = ConfigDict(from_attributes=True)
