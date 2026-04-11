from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class UserBase(BaseModel):
    email: str = Field(max_length=255)

class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=255)

class UserUpdate(BaseModel):
    email: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=255)

class UserRead(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
