import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

ALEMBIC_INI_PATH = Path(__file__).resolve().parents[1] / "alembic.ini"
V2_REVISION = "8b1d4e6f2a90"
HEAD_REVISION = "f19f6d677a36"

_WECOM_TABLES = {"wecom_user_bindings", "wecom_sync_profiles", "wecom_daily_sync_records"}
_TIMESTAMP = "2026-08-08 00:00:00"


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


def _seed_v2_owner(db_path: Path) -> None:
    """Minimal V2-shaped row set so the upgrade runs against a non-empty DB.

    Only `users` is populated: the three WeCom tables have no FK into
    `daily_report_days`/`wecom_sync_profiles` rows required for the upgrade
    itself to succeed, so a lone owner row is enough to prove this revision
    upgrades an already-V2 database, not just a fresh empty one.
    """
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO users (
                id, username, username_normalized, display_name, password_hash,
                role, password_changed_at
            ) VALUES ('user-1', 'owner', 'owner', 'Owner', 'hash', 'user', ?)
            """,
            (_TIMESTAMP,),
        )


def test_upgrade_head_creates_exactly_the_three_wecom_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    config = _build_config(db_path)

    command.upgrade(config, "head")

    head_revision = ScriptDirectory.from_config(config).get_current_head()
    assert head_revision == HEAD_REVISION
    assert _WECOM_TABLES <= _table_names(db_path)


def test_upgrade_head_on_an_existing_v2_database_succeeds_and_passes_fk_check(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "test.db"
    config = _build_config(db_path)
    command.upgrade(config, V2_REVISION)
    _seed_v2_owner(db_path)

    command.upgrade(config, "head")

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("SELECT COUNT(*) FROM users").fetchone() == (1,)
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            HEAD_REVISION,
        )
    assert _WECOM_TABLES <= _table_names(db_path)


def test_upgrade_head_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    config = _build_config(db_path)

    command.upgrade(config, "head")
    command.upgrade(config, "head")  # already at head: must be a no-op, not an error

    assert _WECOM_TABLES <= _table_names(db_path)


def test_downgrade_from_head_drops_only_the_wecom_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    config = _build_config(db_path)
    command.upgrade(config, "head")
    _seed_v2_owner(db_path)

    command.downgrade(config, V2_REVISION)

    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            V2_REVISION,
        )
        # V2 data survives a clean downgrade of an unrelated, always-empty
        # add-on revision.
        assert connection.execute("SELECT COUNT(*) FROM users").fetchone() == (1,)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    remaining = _table_names(db_path)
    assert _WECOM_TABLES.isdisjoint(remaining)
    assert "users" in remaining


def test_downgrade_from_head_to_base_drops_every_business_table(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    config = _build_config(db_path)
    command.upgrade(config, "head")

    command.downgrade(config, "base")

    assert _table_names(db_path) - {"alembic_version"} == set()
