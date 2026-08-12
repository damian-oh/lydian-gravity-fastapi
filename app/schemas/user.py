from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.common import UTCDateTime


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
        # Runs only when the field is present in the payload, so an omitted
        # email still defaults to None; an explicit null is rejected because
        # the column is NOT NULL and clearing an email makes no sense.
        if value is None:
            raise ValueError("email cannot be null.")

        return value.strip().lower()

    model_config = ConfigDict(extra="forbid")


class UserPasswordUpdate(BaseModel):
    current_password: str = Field(min_length=8, max_length=255)
    new_password: str = Field(min_length=8, max_length=255)

    model_config = ConfigDict(extra="forbid")


class UserRead(UserBase):
    id: int
    created_at: UTCDateTime
    is_demo: bool

    model_config = ConfigDict(from_attributes=True)
