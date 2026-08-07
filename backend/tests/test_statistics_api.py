from datetime import date

from conftest import STAGE5_RUNTIME_HEADERS
from fastapi.testclient import TestClient

from app.core.config import Settings


def test_monthly_statistics_requires_authentication(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, _headers, _settings = stage5_context
    response = client.get(
        "/api/v1/statistics/monthly",
        headers=STAGE5_RUNTIME_HEADERS,
        params={"month": "2026-08"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == 40102


def test_monthly_statistics_rejects_malformed_month(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    response = client.get("/api/v1/statistics/monthly", headers=headers, params={"month": "2026-8"})
    assert response.status_code == 400
    assert response.json()["code"] == 40001


def test_monthly_statistics_rejects_invalid_calendar_month(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    response = client.get(
        "/api/v1/statistics/monthly", headers=headers, params={"month": "2026-13"}
    )
    assert response.status_code == 400
    assert response.json()["code"] == 40001


def test_monthly_statistics_returns_the_documented_shape_for_the_current_month(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    today = date.today()
    month = f"{today.year:04d}-{today.month:02d}"

    response = client.get("/api/v1/statistics/monthly", headers=headers, params={"month": month})

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["month"] == month
    assert data["effective_date_to"] == today.isoformat()
    assert data["denominator_days"] == today.day
    assert data["completed_days"] == 0
    assert data["completion_rate"] == 0.0
    assert data["daily_report_count"] == 0
    assert data["weekly_report_count"] == 0
    assert data["current_streak_days"] == 0
    assert data["days"] == []


def test_monthly_statistics_isolates_owners(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, admin_headers, _settings = stage5_context
    created = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "username": "alice",
            "password": "alice secure password",
            "display_name": "Alice",
            "role": "user",
        },
    )
    assert created.status_code == 200, created.text
    login = client.post(
        "/api/v1/auth/login",
        headers=STAGE5_RUNTIME_HEADERS,
        json={"username": "alice", "password": "alice secure password"},
    )
    alice_headers = {
        **STAGE5_RUNTIME_HEADERS,
        "Authorization": f"Bearer {login.json()['data']['access_token']}",
    }
    today = date.today()
    month = f"{today.year:04d}-{today.month:02d}"

    alice_response = client.get(
        "/api/v1/statistics/monthly", headers=alice_headers, params={"month": month}
    )

    assert alice_response.status_code == 200, alice_response.text
    assert alice_response.json()["data"]["daily_report_count"] == 0
