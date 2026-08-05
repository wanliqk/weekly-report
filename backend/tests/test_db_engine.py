from pathlib import Path
from typing import Annotated

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.engine import create_engine
from app.db.session import create_session_factory, get_db_session
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(environment="test", data_dir=tmp_path)


async def test_sqlite_pragmas_have_the_expected_connection_values(settings: Settings) -> None:
    engine = create_engine(settings)
    try:
        async with engine.connect() as connection:
            foreign_keys = (await connection.execute(text("PRAGMA foreign_keys"))).scalar_one()
            journal_mode = (await connection.execute(text("PRAGMA journal_mode"))).scalar_one()
            synchronous = (await connection.execute(text("PRAGMA synchronous"))).scalar_one()
            busy_timeout = (await connection.execute(text("PRAGMA busy_timeout"))).scalar_one()
    finally:
        await engine.dispose()

    assert foreign_keys == 1
    assert journal_mode == "wal"
    assert synchronous == 1  # NORMAL
    assert busy_timeout == 5000


async def test_pragmas_are_reapplied_on_every_new_pooled_connection(settings: Settings) -> None:
    engine = create_engine(settings)
    try:
        for _ in range(2):
            async with engine.connect() as connection:
                foreign_keys = (await connection.execute(text("PRAGMA foreign_keys"))).scalar_one()
                assert foreign_keys == 1
    finally:
        await engine.dispose()


async def test_session_factory_produces_working_sessions(settings: Settings) -> None:
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar_one() == 1
    finally:
        await engine.dispose()


def test_get_db_session_dependency_yields_a_working_session_end_to_end(tmp_path: Path) -> None:
    runtime_secret = "a" * 32
    app_settings = Settings(environment="test", data_dir=tmp_path, runtime_secret=runtime_secret)
    application = create_app(app_settings)

    @application.get("/__test/db-ping")
    async def _ping(session: Annotated[AsyncSession, Depends(get_db_session)]) -> dict[str, int]:
        result = await session.execute(text("SELECT 1"))
        return {"value": result.scalar_one()}

    with TestClient(application) as client:
        response = client.get("/__test/db-ping", headers={"X-Runtime-Secret": runtime_secret})

    assert response.status_code == 200
    assert response.json() == {"value": 1}
