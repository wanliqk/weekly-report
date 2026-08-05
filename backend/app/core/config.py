from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]

MIN_RUNTIME_SECRET_LENGTH = 32
DATABASE_FILE_NAME = "weekly-report.db"


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
    log_dir: Path = PROJECT_ROOT / ".local-data" / "logs"
    backup_dir: Path = PROJECT_ROOT / ".local-data" / "backups"
    runtime_secret: str | None = None
    cors_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]

    @field_validator("data_dir", "log_dir", "backup_dir", mode="after")
    @classmethod
    def _resolve_absolute_path(cls, value: Path) -> Path:
        return value.resolve()

    @property
    def database_path(self) -> Path:
        return self.data_dir / DATABASE_FILE_NAME

    @model_validator(mode="after")
    def _require_runtime_secret_outside_tests(self) -> Self:
        if self.environment == "test":
            return self
        if self.runtime_secret is None or len(self.runtime_secret) < MIN_RUNTIME_SECRET_LENGTH:
            raise ValueError(
                "runtime_secret is required and must be at least "
                f"{MIN_RUNTIME_SECRET_LENGTH} characters outside the test environment"
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
