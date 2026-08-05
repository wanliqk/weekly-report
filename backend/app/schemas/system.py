from pydantic import BaseModel, Field, field_validator

from app.schemas.user import UserData


class BootstrapStatusData(BaseModel):
    initialized: bool


class BootstrapAdminRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)

    @field_validator("username")
    @classmethod
    def _strip_valid_username(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 3:
            raise ValueError("must contain at least 3 non-whitespace characters")
        return stripped

    @field_validator("display_name")
    @classmethod
    def _strip_non_blank_display_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class BootstrapAdminData(UserData):
    pass
