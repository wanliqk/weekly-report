from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from wecom_service_support import build_template_info

from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.core.ulid import generate_ulid
from app.db.migrate import run_startup_migrations
from app.integrations.wecom.client import WeComInternalClient
from app.integrations.wecom.schemas import WeComTemplateInfo
from app.main import create_app
from app.services.bootstrap import DEFAULT_ADMIN_PASSWORD

RUNTIME_SECRET = "r" * 32
MAIN_BRIDGE_SECRET = "m" * 32
JWT_SECRET = "j" * 64
PASSWORD = "correct horse battery staple"
RUNTIME_HEADERS = {"X-Runtime-Secret": RUNTIME_SECRET}

_COOKIE_JAR: list[dict[str, Any]] = [
    {
        "name": "wedoc_sid",
        "value": "SYNTHETIC-SID",
        "domain": "doc.weixin.qq.com",
        "path": "/",
        "secure": True,
        "http_only": True,
        "same_site": "lax",
        "expiration_date": None,
    }
]


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        environment="test",
        data_dir=tmp_path / "data",
        backup_dir=tmp_path / "backups",
        runtime_secret=RUNTIME_SECRET,
        main_bridge_secret=MAIN_BRIDGE_SECRET,
    )
    ensure_runtime_directories(settings)
    run_startup_migrations(settings)
    with TestClient(create_app(settings, jwt_secret=JWT_SECRET)) as test_client:
        yield test_client


def _bootstrap(client: TestClient, *, username: str = "alice") -> None:
    response = client.post(
        "/api/v1/system/bootstrap",
        headers=RUNTIME_HEADERS,
        json={"username": username, "password": PASSWORD, "display_name": "Alice"},
    )
    assert response.status_code == 200, response.text


def _login(client: TestClient, *, username: str) -> dict[str, str]:
    # The fixed `admin` account always bootstraps with its own default
    # password (`BootstrapService.DEFAULT_ADMIN_PASSWORD`), never the
    # requested user's password.
    password = DEFAULT_ADMIN_PASSWORD if username == "admin" else PASSWORD
    response = client.post(
        "/api/v1/auth/login",
        headers=RUNTIME_HEADERS,
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    token = cast(str, response.json()["data"]["access_token"])
    return {**RUNTIME_HEADERS, "Authorization": f"Bearer {token}"}


def _bootstrap_and_login(
    client: TestClient, *, username: str = "alice", login_as: str | None = None
) -> dict[str, str]:
    _bootstrap(client, username=username)
    return _login(client, username=login_as or username)


def _admin_headers_after_forced_password_change(client: TestClient) -> dict[str, str]:
    """The auto-created `admin` account always starts with
    `must_change_password=True` (`docs/方案设计.md` §10A); every other business
    endpoint — including this task's — rejects it with `40303` until the
    password is changed, so any test that needs a *usable* admin session must
    clear that first.
    """
    initial_headers = _login(client, username="admin")
    new_password = "changed admin password for wecom tests"
    change = client.put(
        "/api/v1/auth/password",
        headers=initial_headers,
        json={"current_password": DEFAULT_ADMIN_PASSWORD, "new_password": new_password},
    )
    assert change.status_code == 200, change.text
    relogin = client.post(
        "/api/v1/auth/login",
        headers=RUNTIME_HEADERS,
        json={"username": "admin", "password": new_password},
    )
    assert relogin.status_code == 200, relogin.text
    token = cast(str, relogin.json()["data"]["access_token"])
    return {**RUNTIME_HEADERS, "Authorization": f"Bearer {token}"}


def _create(client: TestClient, headers: dict[str, str], work_date: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/daily-reports",
        headers=headers,
        json={"work_date": work_date, "client_request_id": generate_ulid()},
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json()["data"])


def _content_for_every_enabled_field(report: dict[str, Any]) -> dict[str, object]:
    return {
        field["field_key"]: f"{field['label']}内容"
        for field in report["template_snapshot"]
        if field["enabled"]
    }


def _submit(client: TestClient, headers: dict[str, str], report: dict[str, Any]) -> dict[str, Any]:
    save = client.patch(
        f"/api/v1/daily-reports/{report['id']}",
        headers=headers,
        json={"version": report["version"], "content": _content_for_every_enabled_field(report)},
    )
    assert save.status_code == 200, save.text
    submit = client.post(
        f"/api/v1/daily-reports/{report['id']}/submit",
        headers=headers,
        json={"version": save.json()["data"]["version"]},
    )
    assert submit.status_code == 200, submit.text
    return cast(dict[str, Any], submit.json()["data"])


def _archive(client: TestClient, headers: dict[str, str], work_date: str) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/daily-report-days/{work_date}/archive",
        headers=headers,
        json={"confirm_archive": True},
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json()["data"])


def _archived_day_id(client: TestClient, headers: dict[str, str], work_date: str) -> str:
    report = _create(client, headers, work_date)
    _submit(client, headers, report)
    _archive(client, headers, work_date)
    return cast(str, report["day_id"])


def _connect(
    client: TestClient,
    headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    *,
    template_info: WeComTemplateInfo | None = None,
) -> None:
    resolved = template_info if template_info is not None else build_template_info()

    async def _fake_get_template_info(
        self: WeComInternalClient, cookie_jar: object, form_id: str
    ) -> WeComTemplateInfo:
        return resolved

    monkeypatch.setattr(WeComInternalClient, "get_template_info", _fake_get_template_info)
    internal_headers = {**headers, "X-Main-Bridge-Secret": MAIN_BRIDGE_SECRET}
    response = client.post(
        "/api/v1/internal/wecom/connections/validate",
        headers=internal_headers,
        json={"cookie_jar": _COOKIE_JAR, "credential_slot": "slot-1", "form_id": "form-1"},
    )
    assert response.status_code == 200, response.text


def test_connection_and_profile_before_any_connect(client: TestClient) -> None:
    headers = _bootstrap_and_login(client)

    connection = client.get("/api/v1/wecom/connection", headers=headers)
    assert connection.status_code == 200, connection.text
    data = connection.json()["data"]
    assert data["connected"] is False
    assert data["status"] is None

    profile = client.get("/api/v1/wecom/profile", headers=headers)
    assert profile.status_code == 409
    assert profile.json()["code"] == 40911


def test_previews_and_day_sync_creation_require_an_archived_day(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _bootstrap_and_login(client)
    _connect(client, headers, monkeypatch)
    report = _create(client, headers, "2026-08-05")

    preview = client.post(
        "/api/v1/wecom/previews",
        headers=headers,
        json={"daily_report_day_id": report["day_id"]},
    )
    assert preview.status_code == 409
    assert preview.json()["code"] == 40902

    day_sync = client.post("/api/v1/daily-report-days/2026-08-05/wecom-syncs", headers=headers)
    assert day_sync.status_code == 409
    assert day_sync.json()["code"] == 40902


def test_full_public_flow_after_connecting_and_archiving(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _bootstrap_and_login(client)
    _connect(client, headers, monkeypatch)
    day_id = _archived_day_id(client, headers, "2026-08-05")

    connection = client.get("/api/v1/wecom/connection", headers=headers).json()["data"]
    assert connection["connected"] is True
    assert connection["status"] == "connected"

    profile = client.get("/api/v1/wecom/profile", headers=headers).json()["data"]
    assert profile["version"] == 1
    assert profile["field_mapping"]["unmapped_policy"] == "block"

    update = client.put(
        "/api/v1/wecom/profile",
        headers=headers,
        json={
            "expected_version": 1,
            "recipient_config": {
                "schema_version": 1,
                "mngreporter_vids": ["9000000000000099"],
                "reporter_vids": [],
                "remote_version": 1,
            },
        },
    )
    assert update.status_code == 200, update.text
    assert update.json()["data"]["version"] == 2
    assert update.json()["data"]["recipient_config"]["mngreporter_vids"] == ["9000000000000099"]

    stale_update = client.put(
        "/api/v1/wecom/profile", headers=headers, json={"expected_version": 1}
    )
    assert stale_update.status_code == 409
    assert stale_update.json()["code"] == 40904

    preview = client.post(
        "/api/v1/wecom/previews", headers=headers, json={"daily_report_day_id": day_id}
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["data"]["source_count"] == 1

    created = client.post("/api/v1/daily-report-days/2026-08-05/wecom-syncs", headers=headers)
    assert created.status_code == 200, created.text
    created_data = created.json()["data"]
    assert created_data["created"] is True
    assert created_data["status"] == "pending"
    record_id = created_data["id"]

    idempotent = client.post("/api/v1/daily-report-days/2026-08-05/wecom-syncs", headers=headers)
    assert idempotent.status_code == 200, idempotent.text
    assert idempotent.json()["data"]["created"] is False
    assert idempotent.json()["data"]["id"] == record_id

    listing = client.get("/api/v1/wecom/sync-records", headers=headers)
    assert listing.status_code == 200, listing.text
    assert listing.json()["data"]["total"] == 1
    assert listing.json()["data"]["items"][0]["work_date"] == "2026-08-05"

    detail = client.get(f"/api/v1/wecom/sync-records/{record_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["data"]["status"] == "pending"

    retry = client.post(f"/api/v1/wecom/sync-records/{record_id}/retry", headers=headers)
    assert retry.status_code == 200, retry.text
    assert retry.json()["data"]["status"] == "pending"

    missing = client.get(f"/api/v1/wecom/sync-records/{generate_ulid()}", headers=headers)
    assert missing.status_code == 404


def test_sync_records_are_isolated_per_owner(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bootstrap(client, username="owner")
    owner_headers = _login(client, username="owner")
    # Bootstrap always creates a fixed `admin` account alongside the given
    # username (`docs/方案设计.md` §10A's double-account bootstrap); use it to
    # create a second, unrelated regular account for the isolation check.
    admin_headers = _admin_headers_after_forced_password_change(client)
    create_stranger = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "username": "stranger",
            "password": "stranger secure password",
            "display_name": "Stranger",
            "role": "user",
        },
    )
    assert create_stranger.status_code == 200, create_stranger.text
    stranger_login = client.post(
        "/api/v1/auth/login",
        headers=RUNTIME_HEADERS,
        json={"username": "stranger", "password": "stranger secure password"},
    )
    assert stranger_login.status_code == 200
    stranger_token = stranger_login.json()["data"]["access_token"]
    stranger_headers = {**RUNTIME_HEADERS, "Authorization": f"Bearer {stranger_token}"}

    _connect(client, owner_headers, monkeypatch)
    _archived_day_id(client, owner_headers, "2026-08-05")
    created = client.post("/api/v1/daily-report-days/2026-08-05/wecom-syncs", headers=owner_headers)
    assert created.status_code == 200, created.text
    record_id = created.json()["data"]["id"]

    stranger_get = client.get(f"/api/v1/wecom/sync-records/{record_id}", headers=stranger_headers)
    assert stranger_get.status_code == 404

    stranger_list = client.get("/api/v1/wecom/sync-records", headers=stranger_headers)
    assert stranger_list.status_code == 200
    assert stranger_list.json()["data"]["total"] == 0

    stranger_connection = client.get("/api/v1/wecom/connection", headers=stranger_headers)
    assert stranger_connection.json()["data"]["connected"] is False


def test_public_endpoints_require_authentication(client: TestClient) -> None:
    _bootstrap_and_login(client)
    response = client.get("/api/v1/wecom/connection", headers=RUNTIME_HEADERS)
    assert response.status_code == 401


def test_public_endpoints_are_blocked_before_forced_password_change(client: TestClient) -> None:
    headers = _bootstrap_and_login(client, login_as="admin")
    response = client.get("/api/v1/wecom/connection", headers=headers)
    assert response.status_code == 403
    assert response.json()["code"] == 40303
