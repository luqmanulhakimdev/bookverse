from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().casefold()


class UserPublic(BaseModel):
    id: UUID
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LibraryItemInput(BaseModel):
    status: str = "want_to_read"
    rating: int | None = Field(default=None, ge=1, le=5)
    progress: int | None = Field(default=None, ge=0, le=100)

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        if value not in {"want_to_read", "reading", "finished"}:
            raise ValueError("Invalid reading status")
        return value
