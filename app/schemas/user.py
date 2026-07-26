from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserBase(BaseModel):
    email: EmailStr = Field(max_length=255)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=255)

    model_config = ConfigDict(extra="forbid")


class UserUpdate(BaseModel):
    email: EmailStr | None = Field(default=None, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return value.strip().lower()

    model_config = ConfigDict(extra="forbid")


class UserPasswordUpdate(BaseModel):
    current_password: str = Field(min_length=8, max_length=255)
    new_password: str = Field(min_length=8, max_length=255)

    model_config = ConfigDict(extra="forbid")


class UserRead(UserBase):
    id: int
    created_at: datetime
    is_demo: bool

    model_config = ConfigDict(from_attributes=True)
