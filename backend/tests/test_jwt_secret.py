from pathlib import Path

import pytest

from app.core.jwt_secret import JWT_SECRET_FILE_NAME, load_or_create_jwt_secret


def test_jwt_secret_is_created_once_and_reused(tmp_path: Path) -> None:
    first = load_or_create_jwt_secret(tmp_path)
    second = load_or_create_jwt_secret(tmp_path)

    assert first == second
    assert len(first) == 64
    assert bytes.fromhex(first)
    assert (tmp_path / JWT_SECRET_FILE_NAME).read_text(encoding="utf-8") == first


@pytest.mark.parametrize("invalid_value", ["", "too-short", "z" * 64])
def test_invalid_existing_jwt_secret_stops_startup(tmp_path: Path, invalid_value: str) -> None:
    (tmp_path / JWT_SECRET_FILE_NAME).write_text(invalid_value, encoding="utf-8")

    with pytest.raises(RuntimeError, match="JWT signing secret file is invalid"):
        load_or_create_jwt_secret(tmp_path)
