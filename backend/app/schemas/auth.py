from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_serializer, field_validator

from app.schemas.user import UserData


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def _strip_username(cls, value: str) -> str:
        return value.strip()


class LoginData(BaseModel):
    access_token: str
    expires_at: datetime

    @field_serializer("expires_at")
    def _serialize_expires_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat()


class MeData(UserData):
    must_change_password: bool


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class EmptyData(BaseModel):
    pass
