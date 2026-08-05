from pydantic import BaseModel


class SettingsData(BaseModel):
    auto_archive_on_submit: bool
    timezone: str


class SettingsUpdateRequest(BaseModel):
    auto_archive_on_submit: bool


class CapabilitiesData(BaseModel):
    wecom_sync: bool = False
