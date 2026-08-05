from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BootstrapStatusData(BaseModel):
    initialized: bool


class BootstrapAdminRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)


class BootstrapAdminData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime
