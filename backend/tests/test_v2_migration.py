import json
import sqlite3
from pathlib import Path

import pytest

from alembic import command
from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.db.migrate import _build_alembic_config, run_startup_migrations

V1_REVISION = "3f6f955b87bb"
HEAD_REVISION = "8b1d4e6f2a90"
USER_ID = "user-1"
INACTIVE_USER_ID = "user-2"
TEMPLATE_ID = "template-1"
VERSION_ID = "version-1"
VERSION_2_ID = "version-2"
ARCHIVED_ID = "daily-archived"
DRAFT_ID = "daily-draft"
SUBMITTED_ID = "daily-submitted"
WEEKLY_ID = "weekly-1"
EXPORT_ID = "export-1"
TIMESTAMP = "2026-08-05 12:00:00"
LEGACY_WEEKLY_CONTENT = (
    '{"days":[{"work_date":"2025-12-31","daily_report_id":"daily-archived",'
    '"fields":[{"field_key":"today","label":"今日工作","value":"完成迁移"}]}],'
    '"supplement":"补充","next_week_plan":"计划","risks":"风险"}'
)
LEGACY_WEEKLY_SOURCE = '[{"daily_report_id":"daily-archived","work_date":"2025-12-31"}]'


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    result = Settings(
        environment="test",
        data_dir=tmp_path / "data",
        backup_dir=tmp_path / "backups",
    )
    ensure_runtime_directories(result)
    return result


def _upgrade_to_v1_and_seed(settings: Settings) -> None:
    command.upgrade(_build_alembic_config(settings), V1_REVISION)
    with sqlite3.connect(settings.database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO users (
                id, username, username_normalized, display_name, password_hash,
                role, token_version, is_active, password_changed_at, created_at, updated_at
            ) VALUES (?, 'owner', 'owner', 'Owner', 'hash', 'user', 1, 1, ?, ?, ?)
            """,
            (USER_ID, TIMESTAMP, TIMESTAMP, TIMESTAMP),
        )
        connection.execute(
            """
            INSERT INTO users (
                id, username, username_normalized, display_name, password_hash,
                role, token_version, is_active, password_changed_at, created_at, updated_at
            ) VALUES (?, 'inactive', 'inactive', 'Inactive', 'hash', 'user', 2, 0, ?, ?, ?)
            """,
            (INACTIVE_USER_ID, TIMESTAMP, TIMESTAMP, TIMESTAMP),
        )
        connection.execute(
            """
            INSERT INTO report_templates (
                id, user_id, name, current_version_no, created_at, updated_at
            ) VALUES (?, ?, '日报模板', 2, ?, ?)
            """,
            (TEMPLATE_ID, USER_ID, TIMESTAMP, TIMESTAMP),
        )
        connection.execute(
            """
            INSERT INTO template_versions (
                id, template_id, version_no, fields_json, created_by, created_at
            ) VALUES (?, ?, 1, ?, ?, ?)
            """,
            (
                VERSION_ID,
                TEMPLATE_ID,
                '[{"field_key":"today","label":"今日工作"}]',
                USER_ID,
                TIMESTAMP,
            ),
        )
        connection.execute(
            """
            INSERT INTO template_versions (
                id, template_id, version_no, fields_json, created_by, created_at
            ) VALUES (?, ?, 2, ?, ?, ?)
            """,
            (
                VERSION_2_ID,
                TEMPLATE_ID,
                '[{"field_key":"today","label":"新版今日工作"}]',
                USER_ID,
                TIMESTAMP,
            ),
        )
        connection.execute(
            """
            INSERT INTO user_settings (
                user_id, auto_archive_on_submit, timezone, created_at, updated_at
            ) VALUES (?, 1, 'Asia/Shanghai', ?, ?)
            """,
            (USER_ID, TIMESTAMP, TIMESTAMP),
        )
        connection.execute(
            """
            INSERT INTO daily_reports (
                id, user_id, work_date, status, template_version_id,
                template_snapshot_json, content_json, version, submitted_at,
                archived_at, created_at, updated_at
            ) VALUES (?, ?, '2025-12-31', 'archived', ?, ?, ?, 3, ?, ?, ?, ?)
            """,
            (
                ARCHIVED_ID,
                USER_ID,
                VERSION_ID,
                '[{"field_key":"today","label":"今日工作"}]',
                '{"today":"完成迁移"}',
                TIMESTAMP,
                TIMESTAMP,
                TIMESTAMP,
                TIMESTAMP,
            ),
        )
        connection.execute(
            """
            INSERT INTO daily_reports (
                id, user_id, work_date, status, template_version_id,
                template_snapshot_json, content_json, version, submitted_at,
                archived_at, created_at, updated_at
            ) VALUES (?, ?, '2030-12-31', 'draft', ?, '[]', '{}', 1, NULL, NULL, ?, ?)
            """,
            (DRAFT_ID, USER_ID, VERSION_ID, TIMESTAMP, TIMESTAMP),
        )
        connection.execute(
            """
            INSERT INTO daily_reports (
                id, user_id, work_date, status, template_version_id,
                template_snapshot_json, content_json, version, submitted_at,
                archived_at, created_at, updated_at
            ) VALUES (
                ?, ?, '2024-02-29', 'submitted', ?, ?, '{"today":"闰日"}',
                2, ?, NULL, ?, ?
            )
            """,
            (
                SUBMITTED_ID,
                USER_ID,
                VERSION_2_ID,
                '[{"field_key":"today","label":"新版今日工作"}]',
                TIMESTAMP,
                TIMESTAMP,
                TIMESTAMP,
            ),
        )
        connection.execute(
            """
            INSERT INTO weekly_reports (
                id, user_id, week_start, week_end, generated_content_json,
                content_json, source_snapshot_json, generated_at, version,
                created_at, updated_at
            ) VALUES (?, ?, '2025-12-29', '2026-01-04', ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                WEEKLY_ID,
                USER_ID,
                LEGACY_WEEKLY_CONTENT,
                LEGACY_WEEKLY_CONTENT,
                LEGACY_WEEKLY_SOURCE,
                TIMESTAMP,
                TIMESTAMP,
                TIMESTAMP,
            ),
        )
        connection.execute(
            """
            INSERT INTO weekly_report_sources (
                weekly_report_id, daily_report_id, work_date, included_at
            ) VALUES (?, ?, '2025-12-31', ?)
            """,
            (WEEKLY_ID, ARCHIVED_ID, TIMESTAMP),
        )
        connection.execute(
            """
            INSERT INTO export_jobs (
                id, user_id, status, request_json, file_name, file_path,
                record_count, error_message, created_at, expires_at
            ) VALUES (?, ?, 'failed', '{}', NULL, NULL, 0, 'test failure', ?, ?)
            """,
            (EXPORT_ID, INACTIVE_USER_ID, TIMESTAMP, "2026-08-06 12:00:00"),
        )


def _column_names(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


def _table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }


def test_v1_data_upgrades_to_v2_and_can_losslessly_downgrade(settings: Settings) -> None:
    _upgrade_to_v1_and_seed(settings)

    run_startup_migrations(settings)

    assert len(list(settings.backup_dir.glob("weekly-report-*.db"))) == 1
    with sqlite3.connect(settings.database_path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            HEAD_REVISION,
        )
        assert "must_change_password" in _column_names(connection, "users")
        assert "auto_archive_on_submit" not in _column_names(connection, "user_settings")
        assert {"daily_report_days", "admin_audit_events"} <= _table_names(connection)
        assert connection.execute(
            "SELECT COUNT(*) FROM users WHERE must_change_password = 0"
        ).fetchone() == (2,)
        assert connection.execute(
            "SELECT is_active, token_version FROM users WHERE id = ?",
            (INACTIVE_USER_ID,),
        ).fetchone() == (0, 2)
        assert connection.execute(
            "SELECT COUNT(*) FROM template_versions WHERE template_id = ?",
            (TEMPLATE_ID,),
        ).fetchone() == (2,)
        assert connection.execute(
            "SELECT user_id, status, request_json FROM export_jobs WHERE id = ?",
            (EXPORT_ID,),
        ).fetchone() == (INACTIVE_USER_ID, "failed", "{}")

        archived_day = connection.execute(
            """
            SELECT status, archive_snapshot_json, source_count, archived_by, version
            FROM daily_report_days WHERE id = ?
            """,
            (ARCHIVED_ID,),
        ).fetchone()
        assert archived_day is not None
        assert archived_day[0] == "archived"
        snapshot = json.loads(str(archived_day[1]))
        assert snapshot["schema_version"] == 2
        assert snapshot["work_date"] == "2025-12-31"
        assert snapshot["entries"] == [
            {
                "daily_report_id": ARCHIVED_ID,
                "submitted_at": "2026-08-05T12:00:00+00:00",
                "template_version_id": VERSION_ID,
                "template_snapshot": [{"field_key": "today", "label": "今日工作"}],
                "content": {"today": "完成迁移"},
            }
        ]
        assert archived_day[2:] == (1, USER_ID, 3)
        assert connection.execute(
            """
            SELECT status, archive_snapshot_json, source_count
            FROM daily_report_days WHERE id = ?
            """,
            (DRAFT_ID,),
        ).fetchone() == ("open", None, 0)
        assert connection.execute(
            """
            SELECT status, archive_snapshot_json, source_count, work_date
            FROM daily_report_days WHERE id = ?
            """,
            (SUBMITTED_ID,),
        ).fetchone() == ("open", None, 0, "2024-02-29")
        assert connection.execute(
            "SELECT work_date FROM daily_report_days WHERE id = ?", (DRAFT_ID,)
        ).fetchone() == ("2030-12-31",)
        assert connection.execute(
            "SELECT day_id, client_request_id FROM daily_reports WHERE id = ?",
            (ARCHIVED_ID,),
        ).fetchone() == (ARCHIVED_ID, ARCHIVED_ID)
        assert connection.execute(
            """
            SELECT template_snapshot_json, content_json, submitted_at, archived_at
            FROM daily_reports WHERE id = ?
            """,
            (ARCHIVED_ID,),
        ).fetchone() == (
            '[{"field_key":"today","label":"今日工作"}]',
            '{"today":"完成迁移"}',
            TIMESTAMP,
            TIMESTAMP,
        )
        assert connection.execute(
            "SELECT daily_report_day_id FROM weekly_report_sources"
        ).fetchone() == (ARCHIVED_ID,)
        weekly_row = connection.execute(
            """
            SELECT generated_content_json, content_json, source_snapshot_json
            FROM weekly_reports WHERE id = ?
            """,
            (WEEKLY_ID,),
        ).fetchone()
        assert weekly_row is not None
        for raw in weekly_row:
            upgraded_weekly = json.loads(str(raw))
            assert upgraded_weekly["schema_version"] == 2
            assert upgraded_weekly["days"][0]["daily_report_day_id"] == ARCHIVED_ID
            assert upgraded_weekly["days"][0]["source_count"] == 1
            assert upgraded_weekly["days"][0]["entries"][0]["daily_report_id"] == ARCHIVED_ID
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []

    command.downgrade(_build_alembic_config(settings), V1_REVISION)

    with sqlite3.connect(settings.database_path) as connection:
        assert "must_change_password" not in _column_names(connection, "users")
        assert "auto_archive_on_submit" in _column_names(connection, "user_settings")
        assert {"daily_report_days", "admin_audit_events"}.isdisjoint(_table_names(connection))
        assert connection.execute(
            "SELECT user_id, work_date FROM daily_reports WHERE id = ?", (ARCHIVED_ID,)
        ).fetchone() == (USER_ID, "2025-12-31")
        assert connection.execute(
            "SELECT daily_report_id FROM weekly_report_sources"
        ).fetchone() == (ARCHIVED_ID,)
        assert connection.execute(
            "SELECT auto_archive_on_submit FROM user_settings WHERE user_id = ?",
            (USER_ID,),
        ).fetchone() == (0,)
        downgraded_weekly = connection.execute(
            """
            SELECT generated_content_json, content_json, source_snapshot_json
            FROM weekly_reports WHERE id = ?
            """,
            (WEEKLY_ID,),
        ).fetchone()
        assert downgraded_weekly is not None
        assert json.loads(str(downgraded_weekly[0])) == json.loads(LEGACY_WEEKLY_CONTENT)
        assert json.loads(str(downgraded_weekly[1])) == json.loads(LEGACY_WEEKLY_CONTENT)
        assert json.loads(str(downgraded_weekly[2])) == json.loads(LEGACY_WEEKLY_SOURCE)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_v2_downgrade_rejects_multiple_entries_for_one_day(settings: Settings) -> None:
    _upgrade_to_v1_and_seed(settings)
    run_startup_migrations(settings)
    with sqlite3.connect(settings.database_path) as connection:
        connection.execute(
            """
            INSERT INTO daily_reports (
                id, day_id, client_request_id, status, template_version_id,
                template_snapshot_json, content_json, version, submitted_at,
                archived_at, created_at, updated_at
            ) VALUES (
                'second-entry', ?, 'second-request', 'draft', ?, '[]', '{}',
                1, NULL, NULL, ?, ?
            )
            """,
            (DRAFT_ID, VERSION_ID, TIMESTAMP, TIMESTAMP),
        )

    with pytest.raises(RuntimeError, match="multiple daily report entries"):
        command.downgrade(_build_alembic_config(settings), V1_REVISION)

    with sqlite3.connect(settings.database_path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            HEAD_REVISION,
        )
        assert "daily_report_days" in _table_names(connection)


def test_v2_upgrade_rejects_invalid_weekly_json_before_schema_changes(
    settings: Settings,
) -> None:
    _upgrade_to_v1_and_seed(settings)
    with sqlite3.connect(settings.database_path) as connection:
        connection.execute(
            "UPDATE weekly_reports SET content_json = 'not-json' WHERE id = ?",
            (WEEKLY_ID,),
        )

    with pytest.raises(RuntimeError, match="invalid content_json"):
        run_startup_migrations(settings)

    assert len(list(settings.backup_dir.glob("weekly-report-*.db"))) == 1
    with sqlite3.connect(settings.database_path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            V1_REVISION,
        )
        assert "must_change_password" not in _column_names(connection, "users")
        assert "daily_report_days" not in _table_names(connection)


def test_v2_downgrade_rejects_existing_admin_audit_events(
    settings: Settings,
) -> None:
    _upgrade_to_v1_and_seed(settings)
    run_startup_migrations(settings)
    with sqlite3.connect(settings.database_path) as connection:
        connection.execute(
            """
            INSERT INTO admin_audit_events (
                id, action, actor_user_id, actor_username_snapshot, target_type,
                target_id, target_owner_id, reason, metadata_json, created_at
            ) VALUES (
                'audit-1', 'daily_submission_revoked', ?, 'owner', 'daily_report',
                ?, ?, 'test reason', '{}', ?
            )
            """,
            (USER_ID, SUBMITTED_ID, USER_ID, TIMESTAMP),
        )

    with pytest.raises(RuntimeError, match="audit events would be lost"):
        command.downgrade(_build_alembic_config(settings), V1_REVISION)

    with sqlite3.connect(settings.database_path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            HEAD_REVISION,
        )
        assert connection.execute("SELECT COUNT(*) FROM admin_audit_events").fetchone() == (1,)
