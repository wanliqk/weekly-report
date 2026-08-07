import asyncio
import sqlite3
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.core.ulid import generate_ulid
from app.db.engine import create_engine
from app.db.migrate import run_startup_migrations
from app.db.session import create_session_factory
from app.main import create_app
from app.models import User
from app.services.user import (
    CannotDeleteSelfError,
    LastActiveAdminError,
    UserHasBusinessRecordsError,
    UserService,
)

RUNTIME_SECRET = "r" * 32
JWT_SECRET = "j" * 64
RUNTIME_HEADERS = {"X-Runtime-Secret": RUNTIME_SECRET}
ADMIN_PASSWORD = "correct horse battery staple"
CHANGED_ADMIN_PASSWORD = "changed admin password"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    app_settings = Settings(
        environment="test",
        data_dir=tmp_path / "data",
        backup_dir=tmp_path / "backups",
        runtime_secret=RUNTIME_SECRET,
    )
    ensure_runtime_directories(app_settings)
    run_startup_migrations(app_settings)
    return app_settings


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings, jwt_secret=JWT_SECRET)) as test_client:
        yield test_client


def _bootstrap(client: TestClient) -> None:
    response = client.post(
        "/api/v1/system/bootstrap",
        headers=RUNTIME_HEADERS,
        json={"username": "owner", "password": ADMIN_PASSWORD, "display_name": "Owner"},
    )
    assert response.status_code == 200


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        headers=RUNTIME_HEADERS,
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return cast(str, response.json()["data"]["access_token"])


def _auth_headers(token: str) -> dict[str, str]:
    return {**RUNTIME_HEADERS, "Authorization": f"Bearer {token}"}


def _admin_headers(client: TestClient) -> dict[str, str]:
    initial_headers = _auth_headers(_login(client, "admin", ADMIN_PASSWORD))
    changed = client.put(
        "/api/v1/auth/password",
        headers=initial_headers,
        json={"current_password": ADMIN_PASSWORD, "new_password": CHANGED_ADMIN_PASSWORD},
    )
    assert changed.status_code == 200
    return _auth_headers(_login(client, "admin", CHANGED_ADMIN_PASSWORD))


def _create_user(
    client: TestClient,
    headers: dict[str, str],
    *,
    username: str = "alice",
    password: str = "alice secure password",
    role: str = "user",
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": username,
            "password": password,
            "display_name": username.title(),
            "role": role,
        },
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json()["data"])


def _delete(
    client: TestClient,
    headers: dict[str, str],
    user_id: str,
    *,
    confirm_username: str,
    reason: str = "测试删除",
) -> Any:
    return client.request(
        "DELETE",
        f"/api/v1/users/{user_id}",
        headers=headers,
        json={"confirm_username": confirm_username, "reason": reason},
    )


def test_admin_can_delete_a_user_with_no_business_records(
    client: TestClient, settings: Settings
) -> None:
    _bootstrap(client)
    headers = _admin_headers(client)
    alice = _create_user(client, headers)

    response = _delete(client, headers, alice["id"], confirm_username=alice["username"])

    assert response.status_code == 200, response.text
    missing = client.get(f"/api/v1/users/{alice['id']}", headers=headers)
    assert missing.status_code == 404
    with sqlite3.connect(settings.database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM user_settings WHERE user_id = ?", (alice["id"],)
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT COUNT(*) FROM report_templates WHERE user_id = ?", (alice["id"],)
        ).fetchone() == (0,)


def test_delete_records_a_whitelisted_audit_event(client: TestClient) -> None:
    _bootstrap(client)
    headers = _admin_headers(client)
    alice = _create_user(client, headers)

    response = _delete(
        client, headers, alice["id"], confirm_username=alice["username"], reason="账号不再使用"
    )
    assert response.status_code == 200, response.text

    audit = client.get("/api/v1/admin/audit-events?action=user_deleted", headers=headers)
    assert audit.status_code == 200, audit.text
    events = audit.json()["data"]["items"]
    assert len(events) == 1
    assert events[0]["target_id"] == alice["id"]
    assert events[0]["reason"] == "账号不再使用"


def test_delete_is_rejected_when_the_user_has_business_records(client: TestClient) -> None:
    _bootstrap(client)
    headers = _admin_headers(client)
    alice = _create_user(client, headers)
    alice_headers = _auth_headers(_login(client, "alice", "alice secure password"))
    created_report = client.post(
        "/api/v1/daily-reports",
        headers=alice_headers,
        json={"work_date": "2026-08-05", "client_request_id": generate_ulid()},
    )
    assert created_report.status_code == 200, created_report.text

    response = _delete(client, headers, alice["id"], confirm_username=alice["username"])

    assert response.status_code == 409
    assert response.json()["code"] == 40910
    still_there = client.get(f"/api/v1/users/{alice['id']}", headers=headers)
    assert still_there.status_code == 200


def test_delete_requires_the_confirmation_username_to_match(client: TestClient) -> None:
    _bootstrap(client)
    headers = _admin_headers(client)
    alice = _create_user(client, headers)

    response = _delete(client, headers, alice["id"], confirm_username="not-alice")

    assert response.status_code == 400
    assert response.json()["code"] == 40001
    still_there = client.get(f"/api/v1/users/{alice['id']}", headers=headers)
    assert still_there.status_code == 200


def test_admin_cannot_delete_their_own_account(client: TestClient) -> None:
    _bootstrap(client)
    headers = _admin_headers(client)
    me = client.get("/api/v1/auth/me", headers=headers).json()["data"]

    response = _delete(client, headers, me["id"], confirm_username=me["username"])

    assert response.status_code == 400
    assert response.json()["code"] == 40001


def test_regular_user_cannot_delete_accounts(client: TestClient) -> None:
    _bootstrap(client)
    headers = _admin_headers(client)
    _create_user(client, headers)
    bob = _create_user(client, headers, username="bob", password="bob secure password")
    alice_headers = _auth_headers(_login(client, "alice", "alice secure password"))

    response = _delete(client, alice_headers, bob["id"], confirm_username=bob["username"])

    assert response.status_code == 403
    assert response.json()["code"] == 40301


def test_deleting_a_nonexistent_user_returns_404(client: TestClient) -> None:
    _bootstrap(client)
    headers = _admin_headers(client)

    response = _delete(client, headers, "01AAAAAAAAAAAAAAAAAAAAAAAA", confirm_username="ghost")

    assert response.status_code == 404
    assert response.json()["code"] == 40401


@pytest.fixture
def migrated_settings(tmp_path: Path) -> Settings:
    settings = Settings(
        environment="test", data_dir=tmp_path / "data", backup_dir=tmp_path / "backups"
    )
    ensure_runtime_directories(settings)
    run_startup_migrations(settings)
    return settings


@pytest.fixture
async def engine(migrated_settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(migrated_settings)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(engine)


async def test_two_admins_concurrently_deleting_each_other_preserve_one_active_admin(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Mirrors `test_concurrent_admin_disables_preserve_one_active_admin`
    (`test_user_service.py`) for physical deletion: `delete_if_no_business_records`
    reuses the same conditional-`DELETE` last-admin guard as `update_account`,
    so a genuine race between two admins deleting each other must still leave
    exactly one active admin standing rather than emptying the table.
    """
    from app.services.bootstrap import BootstrapService

    async with session_factory() as session:
        await BootstrapService(session).bootstrap(
            username="owner", password="first admin password", display_name="Owner"
        )
        first = (
            await session.execute(select(User).where(User.username_normalized == "admin"))
        ).scalar_one()
    async with session_factory() as session:
        second = await UserService(session).create_user(
            username="admin-two",
            password="second admin password",
            display_name="Admin Two",
            role="admin",
        )

    async def _delete_first_by_second() -> None | LastActiveAdminError | CannotDeleteSelfError:
        async with session_factory() as session:
            try:
                await UserService(session).delete_user(
                    second, first.id, confirm_username=first.username, reason="并发删除测试"
                )
                return None
            except (LastActiveAdminError, CannotDeleteSelfError) as error:
                return error

    async def _delete_second_by_first() -> None | LastActiveAdminError | CannotDeleteSelfError:
        async with session_factory() as session:
            try:
                await UserService(session).delete_user(
                    first, second.id, confirm_username=second.username, reason="并发删除测试"
                )
                return None
            except (LastActiveAdminError, CannotDeleteSelfError) as error:
                return error

    results = await asyncio.gather(_delete_first_by_second(), _delete_second_by_first())

    succeeded = [result for result in results if result is None]
    blocked = [result for result in results if isinstance(result, LastActiveAdminError)]
    assert len(succeeded) == 1
    assert len(blocked) == 1
    async with session_factory() as session:
        active_admins = await session.execute(
            select(func.count())
            .select_from(User)
            .where(User.role == "admin", User.is_active.is_(True))
        )
        assert active_admins.scalar_one() == 1


async def test_deleting_a_user_with_business_records_raises_via_the_service(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    from datetime import date

    from app.services.bootstrap import BootstrapService
    from app.services.daily_report import DailyReportService

    async with session_factory() as session:
        ordinary_user = await BootstrapService(session).bootstrap(
            username="owner", password="admin password", display_name="Owner"
        )
        admin = (
            await session.execute(select(User).where(User.username_normalized == "admin"))
        ).scalar_one()

    async with session_factory() as session:
        await DailyReportService(session).create(
            ordinary_user.id, work_date=date(2026, 8, 5), client_request_id=generate_ulid()
        )

    async with session_factory() as session:
        with pytest.raises(UserHasBusinessRecordsError):
            await UserService(session).delete_user(
                admin,
                ordinary_user.id,
                confirm_username=ordinary_user.username,
                reason="业务记录测试",
            )
