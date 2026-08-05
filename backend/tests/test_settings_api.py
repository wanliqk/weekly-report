from fastapi.testclient import TestClient

from app.core.config import Settings


def test_settings_default_update_and_capabilities(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context

    initial = client.get("/api/v1/settings/me", headers=headers)
    updated = client.patch(
        "/api/v1/settings/me",
        headers=headers,
        json={"auto_archive_on_submit": True},
    )
    restored = client.get("/api/v1/settings/me", headers=headers)
    capabilities = client.get("/api/v1/capabilities", headers=headers)

    assert initial.json()["data"] == {
        "auto_archive_on_submit": False,
        "timezone": "Asia/Shanghai",
    }
    assert updated.json()["data"] == {
        "auto_archive_on_submit": True,
        "timezone": "Asia/Shanghai",
    }
    assert restored.json()["data"] == updated.json()["data"]
    assert capabilities.json()["data"] == {"wecom_sync": False}


def test_settings_require_authentication(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, _headers, _settings = stage5_context
    response = client.get("/api/v1/settings/me", headers={"X-Runtime-Secret": "r" * 32})
    assert response.status_code == 401
    assert response.json()["code"] == 40102
