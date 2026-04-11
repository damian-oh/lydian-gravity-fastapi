from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class SongSketchBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    master_tonal_center: str = Field(min_length=1, max_length=10)
    master_mode: str = Field(min_length=1, max_length=20)
    tempo_bpm: int = Field(ge=20, le=300)
    time_signature: str = Field(default="4/4", pattern=r"^\d+/\d+$", max_length=10)
    notes: str | None = None

class SongSketchCreate(SongSketchBase):
    user_id: int = Field(gt=0)

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

class SongSketchRead(SongSketchBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
