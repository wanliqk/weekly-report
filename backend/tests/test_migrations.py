import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

ALEMBIC_INI_PATH = Path(__file__).resolve().parents[1] / "alembic.ini"

_EXPECTED_TABLES = {
    "users",
    "user_settings",
    "report_templates",
    "template_versions",
    "daily_report_days",
    "daily_reports",
    "weekly_reports",
    "weekly_report_sources",
    "export_jobs",
    "admin_audit_events",
    "wecom_user_bindings",
    "wecom_sync_profiles",
    "wecom_daily_sync_records",
}


def _build_config(db_path: Path) -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    config.attributes["sqlalchemy_url"] = f"sqlite+aiosqlite:///{db_path}"
    return config


def _table_names(db_path: Path) -> set[str]:
    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    finally:
        connection.close()
    return {row[0] for row in rows}


def test_upgrade_head_succeeds_on_an_empty_database_and_stamps_head(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    config = _build_config(db_path)

    command.upgrade(config, "head")

    head_revision = ScriptDirectory.from_config(config).get_current_head()
    connection = sqlite3.connect(db_path)
    try:
        current_revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[
            0
        ]
    finally:
        connection.close()

    assert current_revision == head_revision


def test_upgrade_head_creates_exactly_the_tables_in_database_md(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    command.upgrade(_build_config(db_path), "head")

    assert _table_names(db_path) - {"alembic_version"} == _EXPECTED_TABLES


def test_upgrade_head_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    config = _build_config(db_path)

    command.upgrade(config, "head")
    command.upgrade(config, "head")  # already at head: must be a no-op, not an error

    assert _table_names(db_path) - {"alembic_version"} == _EXPECTED_TABLES


def test_downgrade_from_head_drops_all_business_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    config = _build_config(db_path)
    command.upgrade(config, "head")

    command.downgrade(config, "base")

    assert _table_names(db_path) - {"alembic_version"} == set()
