from collections.abc import Iterator, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from wecom_service_support import (
    DEFAULT_FORM_ID,
    build_fork_item,
    build_form_detail,
    build_submission_result,
    build_template_info,
)

from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.core.ulid import generate_ulid
from app.db.migrate import run_startup_migrations
from app.integrations.wecom.client import WeComInternalClient
from app.integrations.wecom.schemas import (
    WeComCookieIn,
    WeComFormDetail,
    WeComSubmissionResult,
    WeComSubmitDailyPayload,
    WeComTemplateInfo,
)
from app.main import create_app

RUNTIME_SECRET = "r" * 32
MAIN_BRIDGE_SECRET = "m" * 32
JWT_SECRET = "j" * 64
PASSWORD = "correct horse battery staple"
RUNTIME_HEADERS = {"X-Runtime-Secret": RUNTIME_SECRET}
MAIN_BRIDGE_HEADER = {"X-Main-Bridge-Secret": MAIN_BRIDGE_SECRET}

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


def _bootstrap_and_login(client: TestClient, *, username: str = "alice") -> dict[str, str]:
    bootstrap = client.post(
        "/api/v1/system/bootstrap",
        headers=RUNTIME_HEADERS,
        json={"username": username, "password": PASSWORD, "display_name": "Alice"},
    )
    assert bootstrap.status_code == 200, bootstrap.text
    login = client.post(
        "/api/v1/auth/login",
        headers=RUNTIME_HEADERS,
        json={"username": username, "password": PASSWORD},
    )
    assert login.status_code == 200, login.text
    token = cast(str, login.json()["data"]["access_token"])
    return {**RUNTIME_HEADERS, "Authorization": f"Bearer {token}"}


def _create(client: TestClient, headers: dict[str, str], work_date: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/daily-reports",
        headers=headers,
        json={"work_date": work_date, "client_request_id": generate_ulid()},
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json()["data"])


def _submit(client: TestClient, headers: dict[str, str], report: dict[str, Any]) -> dict[str, Any]:
    content = {
        field["field_key"]: f"{field['label']}内容"
        for field in report["template_snapshot"]
        if field["enabled"]
    }
    save = client.patch(
        f"/api/v1/daily-reports/{report['id']}",
        headers=headers,
        json={"version": report["version"], "content": content},
    )
    assert save.status_code == 200, save.text
    submit = client.post(
        f"/api/v1/daily-reports/{report['id']}/submit",
        headers=headers,
        json={"version": save.json()["data"]["version"]},
    )
    assert submit.status_code == 200, submit.text
    return cast(dict[str, Any], submit.json()["data"])


def _archive(client: TestClient, headers: dict[str, str], work_date: str) -> None:
    response = client.post(
        f"/api/v1/daily-report-days/{work_date}/archive",
        headers=headers,
        json={"confirm_archive": True},
    )
    assert response.status_code == 200, response.text


def _archived_day(client: TestClient, headers: dict[str, str], work_date: str) -> None:
    report = _create(client, headers, work_date)
    _submit(client, headers, report)
    _archive(client, headers, work_date)


def _patch_get_template_info(
    monkeypatch: pytest.MonkeyPatch, template_info: WeComTemplateInfo | None = None
) -> None:
    resolved = template_info if template_info is not None else build_template_info()

    async def _fake(
        self: WeComInternalClient, cookie_jar: object, form_id: str
    ) -> WeComTemplateInfo:
        return resolved

    monkeypatch.setattr(WeComInternalClient, "get_template_info", _fake)


def _patch_get_form_detail(
    monkeypatch: pytest.MonkeyPatch, form_detail: WeComFormDetail | None = None
) -> None:
    resolved = form_detail if form_detail is not None else build_form_detail()

    async def _fake(self: WeComInternalClient, cookie_jar: object, form_id: str) -> WeComFormDetail:
        return resolved

    monkeypatch.setattr(WeComInternalClient, "get_form_detail", _fake)


def _patch_submit_daily(
    monkeypatch: pytest.MonkeyPatch, submission_result: WeComSubmissionResult | None = None
) -> None:
    resolved = submission_result if submission_result is not None else build_submission_result()

    async def _fake(
        self: WeComInternalClient,
        cookie_jar: Sequence[WeComCookieIn],
        payload: WeComSubmitDailyPayload,
    ) -> WeComSubmissionResult:
        return resolved

    monkeypatch.setattr(WeComInternalClient, "submit_daily", _fake)


def _shanghai_noon_epoch(work_date: date) -> int:
    return int(
        datetime(work_date.year, work_date.month, work_date.day, 4, 0, 0, tzinfo=UTC).timestamp()
    )


def _connect(client: TestClient, headers: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_get_template_info(monkeypatch)
    response = client.post(
        "/api/v1/internal/wecom/connections/validate",
        headers={**headers, **MAIN_BRIDGE_HEADER},
        json={"cookie_jar": _COOKIE_JAR, "credential_slot": "slot-1", "form_id": "form-1"},
    )
    assert response.status_code == 200, response.text


def _login(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        headers=RUNTIME_HEADERS,
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    token = cast(str, response.json()["data"]["access_token"])
    return {**RUNTIME_HEADERS, "Authorization": f"Bearer {token}"}


def _create_second_user(client: TestClient, username: str) -> dict[str, str]:
    admin_headers = _login(client, "admin", PASSWORD)
    changed = client.put(
        "/api/v1/auth/password",
        headers=admin_headers,
        json={"current_password": PASSWORD, "new_password": "new admin password"},
    )
    assert changed.status_code == 200, changed.text
    admin_headers = _login(client, "admin", "new admin password")
    user_password = f"{username} secure password"
    created = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "username": username,
            "password": user_password,
            "display_name": username.title(),
            "role": "user",
        },
    )
    assert created.status_code == 200, created.text
    return _login(client, username, user_password)


def test_internal_endpoints_require_the_main_bridge_secret_header(client: TestClient) -> None:
    headers = _bootstrap_and_login(client)
    response = client.post(
        "/api/v1/internal/wecom/connections/disconnect", headers=headers, json={}
    )
    assert response.status_code == 401
    assert response.json()["code"] == 40104


def test_internal_endpoints_reject_a_wrong_main_bridge_secret(client: TestClient) -> None:
    headers = _bootstrap_and_login(client)
    response = client.post(
        "/api/v1/internal/wecom/connections/disconnect",
        headers={**headers, "X-Main-Bridge-Secret": "n" * 32},
        json={},
    )
    assert response.status_code == 401
    assert response.json()["code"] == 40104


def test_internal_endpoints_still_require_a_jwt(client: TestClient) -> None:
    _bootstrap_and_login(client)
    response = client.post(
        "/api/v1/internal/wecom/connections/disconnect",
        headers=MAIN_BRIDGE_HEADER,
        json={},
    )
    assert response.status_code == 401


def test_internal_endpoints_work_without_the_ordinary_runtime_secret_header(
    client: TestClient,
) -> None:
    """`WeComBridgeClient` never sends `X-Runtime-Secret` (`docs/方案设计.md`
    §3.1/§9.2) — a real end-to-end call from Main carries only the JWT and
    `X-Main-Bridge-Secret`."""
    headers = _bootstrap_and_login(client)
    jwt_only = {"Authorization": headers["Authorization"], **MAIN_BRIDGE_HEADER}
    response = client.post(
        "/api/v1/internal/wecom/connections/disconnect", headers=jwt_only, json={}
    )
    assert response.status_code == 200, response.text


def test_validate_connection_rejects_an_empty_form_id_before_calling_wecom(
    client: TestClient,
) -> None:
    headers = _bootstrap_and_login(client)
    response = client.post(
        "/api/v1/internal/wecom/connections/validate",
        headers={**headers, **MAIN_BRIDGE_HEADER},
        json={"cookie_jar": _COOKIE_JAR, "credential_slot": "slot-1", "form_id": ""},
    )

    assert response.status_code == 400
    assert response.json()["code"] == 40001


def test_internal_endpoints_are_excluded_from_the_public_openapi_schema(
    client: TestClient,
) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert all("/internal/wecom/" not in path for path in paths)
    assert any("/api/v1/wecom/" in path for path in paths)


def test_credential_slot_lookup_is_restart_safe_and_owner_isolated(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    alice_headers = _bootstrap_and_login(client)
    bob_headers = _create_second_user(client, "bob")
    _connect(client, alice_headers, monkeypatch)

    alice_lookup = client.get(
        "/api/v1/internal/wecom/connections/credential-slot",
        headers={**alice_headers, **MAIN_BRIDGE_HEADER},
    )
    bob_lookup = client.get(
        "/api/v1/internal/wecom/connections/credential-slot",
        headers={**bob_headers, **MAIN_BRIDGE_HEADER},
    )

    assert alice_lookup.status_code == 200, alice_lookup.text
    assert alice_lookup.json()["data"] == {
        "credential_slot": "slot-1",
        "connection_status": "connected",
    }
    assert bob_lookup.status_code == 200, bob_lookup.text
    assert bob_lookup.json()["data"] == {
        "credential_slot": None,
        "connection_status": None,
    }

    disconnect_response = client.post(
        "/api/v1/internal/wecom/connections/disconnect",
        headers={**alice_headers, **MAIN_BRIDGE_HEADER},
    )
    assert disconnect_response.status_code == 200, disconnect_response.text
    disconnected_lookup = client.get(
        "/api/v1/internal/wecom/connections/credential-slot",
        headers={**alice_headers, **MAIN_BRIDGE_HEADER},
    )
    assert disconnected_lookup.status_code == 200, disconnected_lookup.text
    assert disconnected_lookup.json()["data"] == {
        "credential_slot": "slot-1",
        "connection_status": "disconnected",
    }


def test_validate_connection_end_to_end_creates_a_connection(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _bootstrap_and_login(client)
    _connect(client, headers, monkeypatch)

    connection = client.get("/api/v1/wecom/connection", headers=headers)
    assert connection.status_code == 200
    assert connection.json()["data"]["connected"] is True


def test_validate_connection_rejects_a_template_missing_target_questions(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.integrations.wecom.schemas import WeComQuestionItem

    headers = _bootstrap_and_login(client)
    incomplete = [
        WeComQuestionItem(question_id="1", title="今日工作", reply_type=1, must_reply=True, pos=1)
    ]
    _patch_get_template_info(monkeypatch, build_template_info(questions=incomplete))
    response = client.post(
        "/api/v1/internal/wecom/connections/validate",
        headers={**headers, **MAIN_BRIDGE_HEADER},
        json={"cookie_jar": _COOKIE_JAR, "credential_slot": "slot-1", "form_id": "form-1"},
    )
    assert response.status_code == 502

    connection = client.get("/api/v1/wecom/connection", headers=headers)
    assert connection.json()["data"]["connected"] is False


def test_disconnect_end_to_end_marks_the_binding_disconnected(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _bootstrap_and_login(client)
    _connect(client, headers, monkeypatch)

    response = client.post(
        "/api/v1/internal/wecom/connections/disconnect",
        headers={**headers, **MAIN_BRIDGE_HEADER},
        json={},
    )
    assert response.status_code == 200, response.text

    connection = client.get("/api/v1/wecom/connection", headers=headers)
    data = connection.json()["data"]
    assert data["connected"] is False
    assert data["status"] == "disconnected"


def test_execute_end_to_end_succeeds_and_updates_the_record(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _bootstrap_and_login(client)
    _connect(client, headers, monkeypatch)
    _archived_day(client, headers, "2026-08-05")
    created = client.post("/api/v1/daily-report-days/2026-08-05/wecom-syncs", headers=headers)
    assert created.status_code == 200, created.text
    record_id = created.json()["data"]["id"]

    _patch_get_form_detail(monkeypatch)
    _patch_submit_daily(monkeypatch)
    response = client.post(
        f"/api/v1/internal/wecom/sync-records/{record_id}/execute",
        headers={**headers, **MAIN_BRIDGE_HEADER},
        json={"cookie_jar": _COOKIE_JAR},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "succeeded"

    detail = client.get(f"/api/v1/wecom/sync-records/{record_id}", headers=headers)
    assert detail.json()["data"]["status"] == "succeeded"


def test_execute_end_to_end_surfaces_a_duplicate_as_a_business_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _bootstrap_and_login(client)
    _connect(client, headers, monkeypatch)
    _archived_day(client, headers, "2026-08-05")
    created = client.post("/api/v1/daily-report-days/2026-08-05/wecom-syncs", headers=headers)
    assert created.status_code == 200, created.text
    record_id = created.json()["data"]["id"]

    candidate = build_fork_item(
        form_id=DEFAULT_FORM_ID,
        ctime=_shanghai_noon_epoch(date(2026, 8, 5)),
    )
    _patch_get_form_detail(monkeypatch, build_form_detail(fork_items=[candidate]))
    _patch_submit_daily(monkeypatch)
    response = client.post(
        f"/api/v1/internal/wecom/sync-records/{record_id}/execute",
        headers={**headers, **MAIN_BRIDGE_HEADER},
        json={"cookie_jar": _COOKIE_JAR},
    )
    assert response.status_code == 409
    assert response.json()["code"] == 40915

    detail = client.get(f"/api/v1/wecom/sync-records/{record_id}", headers=headers)
    assert detail.json()["data"]["status"] == "duplicate_detected"
