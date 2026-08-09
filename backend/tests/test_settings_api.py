from fastapi.testclient import TestClient

from app.core.config import Settings


def test_settings_are_read_only_and_capabilities_remain_available(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context

    initial = client.get("/api/v1/settings/me", headers=headers)
    removed_update = client.patch(
        "/api/v1/settings/me",
        headers=headers,
        json={"auto_archive_on_submit": True},
    )
    capabilities = client.get("/api/v1/capabilities", headers=headers)

    assert initial.json()["data"] == {"timezone": "Asia/Shanghai"}
    assert removed_update.status_code == 405
    assert capabilities.json()["data"] == {"wecom_sync": True}


def test_settings_require_authentication(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, _headers, _settings = stage5_context
    response = client.get("/api/v1/settings/me", headers={"X-Runtime-Secret": "r" * 32})
    assert response.status_code == 401
    assert response.json()["code"] == 40102
