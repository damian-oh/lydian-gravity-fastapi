from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class UserBase(BaseModel):
    email: str = Field(max_length=255)

class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=255)

    model_config = ConfigDict(extra="forbid")

class UserUpdate(BaseModel):
    email: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(extra="forbid")

class UserPasswordUpdate(BaseModel):
    current_password: str = Field(min_length=8, max_length=255)
    new_password: str = Field(min_length=8, max_length=255)

    model_config = ConfigDict(extra="forbid")

class UserRead(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
