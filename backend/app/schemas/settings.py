from pydantic import BaseModel


class SettingsData(BaseModel):
    timezone: str


class CapabilitiesData(BaseModel):
    wecom_sync: bool = False
