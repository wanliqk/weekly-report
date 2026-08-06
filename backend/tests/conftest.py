from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.db.migrate import run_startup_migrations
from app.main import create_app

STAGE5_RUNTIME_SECRET = "r" * 32
STAGE5_JWT_SECRET = "j" * 64
STAGE5_PASSWORD = "correct horse battery staple"
STAGE5_ADMIN_PASSWORD = "changed admin password"
STAGE5_RUNTIME_HEADERS = {"X-Runtime-Secret": STAGE5_RUNTIME_SECRET}


@pytest.fixture
def stage5_context(tmp_path: Path) -> Iterator[tuple[TestClient, dict[str, str], Settings]]:
    settings = Settings(
        environment="test",
        data_dir=tmp_path / "data",
        backup_dir=tmp_path / "backups",
        runtime_secret=STAGE5_RUNTIME_SECRET,
    )
    ensure_runtime_directories(settings)
    run_startup_migrations(settings)
    with TestClient(create_app(settings, jwt_secret=STAGE5_JWT_SECRET)) as client:
        bootstrap = client.post(
            "/api/v1/system/bootstrap",
            headers=STAGE5_RUNTIME_HEADERS,
            json={
                "username": "initial-user",
                "password": STAGE5_PASSWORD,
                "display_name": "Initial User",
            },
        )
        assert bootstrap.status_code == 200
        login = client.post(
            "/api/v1/auth/login",
            headers=STAGE5_RUNTIME_HEADERS,
            json={"username": "admin", "password": STAGE5_PASSWORD},
        )
        assert login.status_code == 200
        initial_token = cast(str, login.json()["data"]["access_token"])
        password_change = client.put(
            "/api/v1/auth/password",
            headers={
                **STAGE5_RUNTIME_HEADERS,
                "Authorization": f"Bearer {initial_token}",
            },
            json={
                "current_password": STAGE5_PASSWORD,
                "new_password": STAGE5_ADMIN_PASSWORD,
            },
        )
        assert password_change.status_code == 200
        changed_login = client.post(
            "/api/v1/auth/login",
            headers=STAGE5_RUNTIME_HEADERS,
            json={"username": "admin", "password": STAGE5_ADMIN_PASSWORD},
        )
        assert changed_login.status_code == 200
        token = cast(str, changed_login.json()["data"]["access_token"])
        headers = {
            **STAGE5_RUNTIME_HEADERS,
            "Authorization": f"Bearer {token}",
        }
        yield client, headers, settings
