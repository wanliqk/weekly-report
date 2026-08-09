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
    export_temp_dir: Path = PROJECT_ROOT / ".local-data" / "temp" / "exports"
    manual_backup_temp_dir: Path = PROJECT_ROOT / ".local-data" / "temp" / "manual-backups"
    # `False` enables additional whitelisted protocol diagnostics in the
    # rotating `wecom.log`; credentials, headers and bodies remain forbidden
    # and are protected independently of this switch.
    wecom_log_redact: bool = True
    # `True` is an explicit, user-authorized troubleshooting exception (not
    # the default posture described by `AGENTS.md`'s general "no report body
    # in logs" rule): it writes raw request/response JSON *bodies* for the
    # three WeCom endpoints to a separate `wecom-raw-debug.log`, gitignored
    # under `.local-data/`. Cookie/header values are never written by this
    # switch, on or off — that boundary is independent of this flag (see
    # `wecom_logging.py`). Must be turned back off once debugging is done;
    # a body can legitimately contain real report text.
    wecom_debug_raw_body: bool = False
    runtime_secret: str | None = None
    # SEC-014 (`docs/方案设计.md` §3.1/§9.2): a second, independent secret from
    # `runtime_secret` — the latter reaches the renderer via preload and can
    # never be trusted to gate the Cookie-carrying `/api/v1/internal/wecom/**`
    # endpoints. Only Electron Main (via its sidecar child-process env) ever
    # holds this value; it must never reach Vite, preload, renderer, logs, or
    # persisted files.
    main_bridge_secret: str | None = None
    cors_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]

    @field_validator(
        "data_dir",
        "log_dir",
        "backup_dir",
        "export_temp_dir",
        "manual_backup_temp_dir",
        mode="after",
    )
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

    @model_validator(mode="after")
    def _require_main_bridge_secret_outside_tests(self) -> Self:
        if self.environment == "test":
            return self
        if (
            self.main_bridge_secret is None
            or len(self.main_bridge_secret) < MIN_RUNTIME_SECRET_LENGTH
        ):
            raise ValueError(
                "main_bridge_secret is required and must be at least "
                f"{MIN_RUNTIME_SECRET_LENGTH} characters outside the test environment"
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
