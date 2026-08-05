from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="WEEKLY_REPORT_",
        extra="ignore",
        frozen=True,
    )

    environment: Literal["development", "test", "production"] = "development"
    host: Literal["127.0.0.1"] = "127.0.0.1"
    port: int = Field(default=0, ge=0, le=65535)
    data_dir: Path = PROJECT_ROOT / ".local-data"
    cors_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
