from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_test_environment_does_not_require_a_runtime_secret() -> None:
    settings = Settings(environment="test")

    assert settings.runtime_secret is None


def test_development_environment_requires_a_runtime_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="development")


def test_short_runtime_secret_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="development", runtime_secret="too-short")


def test_sufficiently_long_runtime_secret_is_accepted() -> None:
    settings = Settings(environment="development", runtime_secret="a" * 32)

    assert settings.runtime_secret == "a" * 32


def test_data_and_log_dir_are_resolved_to_absolute_paths() -> None:
    settings = Settings(
        environment="test",
        data_dir=Path("relative/data"),
        log_dir=Path("relative/logs"),
    )

    assert settings.data_dir.is_absolute()
    assert settings.log_dir.is_absolute()
