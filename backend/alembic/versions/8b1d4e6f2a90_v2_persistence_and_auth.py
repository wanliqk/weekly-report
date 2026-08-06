"""add v2 daily persistence and authentication baseline

Revision ID: 8b1d4e6f2a90
Revises: 3f6f955b87bb
Create Date: 2026-08-07 10:00:00.000000

"""

import json
from collections.abc import Sequence
from datetime import UTC, date, datetime

import sqlalchemy as sa
from sqlalchemy.engine import Connection, RowMapping

from alembic import op

revision: str = "8b1d4e6f2a90"
down_revision: str | Sequence[str] | None = "3f6f955b87bb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _iso_date(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _utc_iso(value: object) -> str:
    if isinstance(value, datetime):
        moment = value
    else:
        moment = datetime.fromisoformat(str(value))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).isoformat()


def _archive_snapshot(row: RowMapping) -> str:
    snapshot = {
        "schema_version": 2,
        "work_date": _iso_date(row["work_date"]),
        "entries": [
            {
                "daily_report_id": str(row["id"]),
                "submitted_at": _utc_iso(row["submitted_at"]),
                "template_version_id": str(row["template_version_id"]),
                "template_snapshot": json.loads(str(row["template_snapshot_json"])),
                "content": json.loads(str(row["content_json"])),
            }
        ],
    }
    return json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))


def _load_weekly_json(raw: object, *, weekly_id: str, column: str) -> object:
    try:
        return json.loads(str(raw))
    except (TypeError, ValueError) as error:
        raise RuntimeError(f"cannot migrate weekly report {weekly_id}: invalid {column}") from error


def _weekly_source_report(
    connection: Connection, *, weekly_id: str, daily_report_id: str
) -> RowMapping:
    row = (
        connection.execute(
            sa.text(
                """
                SELECT report.id, report.day_id, report.submitted_at, day.work_date
                FROM daily_reports AS report
                JOIN daily_report_days AS day ON day.id = report.day_id
                WHERE report.id = :daily_report_id
                """
            ),
            {"daily_report_id": daily_report_id},
        )
        .mappings()
        .first()
    )
    if row is None or row["submitted_at"] is None:
        raise RuntimeError(f"cannot migrate weekly report {weekly_id}: source report is missing")
    return row


def _upgrade_weekly_content(
    connection: Connection, *, weekly_id: str, column: str, raw: object
) -> str:
    value = _load_weekly_json(raw, weekly_id=weekly_id, column=column)
    if not isinstance(value, dict) or not isinstance(value.get("days"), list):
        raise RuntimeError(f"cannot migrate weekly report {weekly_id}: invalid {column} shape")
    upgraded_days: list[dict[str, object]] = []
    for day in value["days"]:
        if not isinstance(day, dict) or not isinstance(day.get("fields"), list):
            raise RuntimeError(f"cannot migrate weekly report {weekly_id}: invalid {column} day")
        daily_report_id = day.get("daily_report_id")
        if not isinstance(daily_report_id, str):
            raise RuntimeError(f"cannot migrate weekly report {weekly_id}: missing daily report id")
        source = _weekly_source_report(
            connection,
            weekly_id=weekly_id,
            daily_report_id=daily_report_id,
        )
        work_date = _iso_date(source["work_date"])
        if day.get("work_date") != work_date:
            raise RuntimeError(f"cannot migrate weekly report {weekly_id}: source date mismatch")
        upgraded_days.append(
            {
                "work_date": work_date,
                "daily_report_day_id": str(source["day_id"]),
                "source_count": 1,
                "entries": [
                    {
                        "daily_report_id": daily_report_id,
                        "submitted_at": _utc_iso(source["submitted_at"]),
                        "fields": day["fields"],
                    }
                ],
            }
        )
    upgraded = {
        "schema_version": 2,
        "days": upgraded_days,
        "supplement": value.get("supplement", ""),
        "next_week_plan": value.get("next_week_plan", ""),
        "risks": value.get("risks", ""),
    }
    if not all(isinstance(upgraded[key], str) for key in ("supplement", "next_week_plan", "risks")):
        raise RuntimeError(f"cannot migrate weekly report {weekly_id}: invalid free-text field")
    return json.dumps(upgraded, ensure_ascii=False, separators=(",", ":"))


def _upgrade_weekly_source_snapshot(connection: Connection, *, weekly_id: str, raw: object) -> str:
    value = _load_weekly_json(raw, weekly_id=weekly_id, column="source_snapshot_json")
    if not isinstance(value, list):
        raise RuntimeError(
            f"cannot migrate weekly report {weekly_id}: invalid source snapshot shape"
        )
    upgraded_days: list[dict[str, object]] = []
    for day in value:
        if not isinstance(day, dict) or not isinstance(day.get("daily_report_id"), str):
            raise RuntimeError(
                f"cannot migrate weekly report {weekly_id}: invalid source snapshot day"
            )
        daily_report_id = str(day["daily_report_id"])
        source = _weekly_source_report(
            connection,
            weekly_id=weekly_id,
            daily_report_id=daily_report_id,
        )
        work_date = _iso_date(source["work_date"])
        if day.get("work_date") != work_date:
            raise RuntimeError(f"cannot migrate weekly report {weekly_id}: source date mismatch")
        upgraded_days.append(
            {
                "work_date": work_date,
                "daily_report_day_id": str(source["day_id"]),
                "source_count": 1,
                "entries": [
                    {
                        "daily_report_id": daily_report_id,
                        "submitted_at": _utc_iso(source["submitted_at"]),
                    }
                ],
            }
        )
    return json.dumps(
        {"schema_version": 2, "days": upgraded_days},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _upgrade_weekly_json(connection: Connection) -> None:
    rows = connection.execute(
        sa.text(
            """
            SELECT id, generated_content_json, content_json, source_snapshot_json
            FROM weekly_reports ORDER BY id
            """
        )
    ).mappings()
    update_weekly = sa.text(
        """
        UPDATE weekly_reports
        SET generated_content_json = :generated_content_json,
            content_json = :content_json,
            source_snapshot_json = :source_snapshot_json
        WHERE id = :id
        """
    )
    for row in rows:
        weekly_id = str(row["id"])
        connection.execute(
            update_weekly,
            {
                "id": weekly_id,
                "generated_content_json": _upgrade_weekly_content(
                    connection,
                    weekly_id=weekly_id,
                    column="generated_content_json",
                    raw=row["generated_content_json"],
                ),
                "content_json": _upgrade_weekly_content(
                    connection,
                    weekly_id=weekly_id,
                    column="content_json",
                    raw=row["content_json"],
                ),
                "source_snapshot_json": _upgrade_weekly_source_snapshot(
                    connection,
                    weekly_id=weekly_id,
                    raw=row["source_snapshot_json"],
                ),
            },
        )


def _create_daily_report_days(connection: Connection) -> None:
    op.create_table(
        "daily_report_days",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("archive_snapshot_json", sa.Text(), nullable=True),
        sa.Column("source_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("archived_by", sa.String(length=26), nullable=True),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint("status IN ('open', 'archived')", name="ck_daily_report_days_status"),
        sa.CheckConstraint(
            "(status = 'open' AND archive_snapshot_json IS NULL AND source_count = 0 "
            "AND archived_by IS NULL AND archived_at IS NULL) OR "
            "(status = 'archived' AND archive_snapshot_json IS NOT NULL AND source_count > 0 "
            "AND archived_by IS NOT NULL AND archived_at IS NOT NULL)",
            name="ck_daily_report_days_archive_state",
        ),
        sa.CheckConstraint("version > 0", name="ck_daily_report_days_version_positive"),
        sa.ForeignKeyConstraint(["archived_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "work_date", name="uq_daily_report_days_user_work_date"),
    )
    op.create_index(
        "ix_daily_report_days_user_date",
        "daily_report_days",
        ["user_id", sa.text("work_date DESC"), sa.text("id DESC")],
        unique=False,
    )
    op.create_index(
        "ix_daily_report_days_user_status_date",
        "daily_report_days",
        ["user_id", "status", sa.text("work_date DESC")],
        unique=False,
    )

    rows = connection.execute(sa.text("SELECT * FROM daily_reports ORDER BY id")).mappings()
    insert_day = sa.text(
        """
        INSERT INTO daily_report_days (
            id, user_id, work_date, status, archive_snapshot_json, source_count,
            archived_by, archived_at, version, created_at, updated_at
        ) VALUES (
            :id, :user_id, :work_date, :status, :archive_snapshot_json, :source_count,
            :archived_by, :archived_at, :version, :created_at, :updated_at
        )
        """
    )
    for row in rows:
        is_archived = row["status"] == "archived"
        connection.execute(
            insert_day,
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "work_date": row["work_date"],
                "status": "archived" if is_archived else "open",
                "archive_snapshot_json": _archive_snapshot(row) if is_archived else None,
                "source_count": 1 if is_archived else 0,
                "archived_by": row["user_id"] if is_archived else None,
                "archived_at": row["archived_at"] if is_archived else None,
                "version": row["version"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            },
        )


def _rebuild_daily_reports() -> None:
    op.execute(
        "CREATE TABLE weekly_report_sources_v1_data AS "
        "SELECT weekly_report_id, daily_report_id, work_date, included_at "
        "FROM weekly_report_sources"
    )
    op.drop_table("weekly_report_sources")

    op.create_table(
        "daily_reports_v2",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("day_id", sa.String(length=26), nullable=False),
        sa.Column("client_request_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("template_version_id", sa.String(length=26), nullable=False),
        sa.Column("template_snapshot_json", sa.Text(), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'submitted', 'archived')", name="ck_daily_reports_status"
        ),
        sa.CheckConstraint(
            "(status = 'draft' AND submitted_at IS NULL AND archived_at IS NULL) OR "
            "(status = 'submitted' AND submitted_at IS NOT NULL AND archived_at IS NULL) OR "
            "(status = 'archived' AND submitted_at IS NOT NULL AND archived_at IS NOT NULL)",
            name="ck_daily_reports_status_timestamps",
        ),
        sa.CheckConstraint("version > 0", name="ck_daily_reports_version_positive"),
        sa.ForeignKeyConstraint(["day_id"], ["daily_report_days.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["template_version_id"], ["template_versions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_request_id", name="uq_daily_reports_client_request_id"),
    )
    op.execute(
        """
        INSERT INTO daily_reports_v2 (
            id, day_id, client_request_id, status, template_version_id,
            template_snapshot_json, content_json, version, submitted_at,
            archived_at, created_at, updated_at
        )
        SELECT id, id, id, status, template_version_id, template_snapshot_json,
               content_json, version, submitted_at, archived_at, created_at, updated_at
        FROM daily_reports
        """
    )
    op.drop_table("daily_reports")
    op.rename_table("daily_reports_v2", "daily_reports")
    op.create_index(
        "ix_daily_reports_day_status_submit",
        "daily_reports",
        ["day_id", "status", "submitted_at", "id"],
        unique=False,
    )

    op.create_table(
        "weekly_report_sources",
        sa.Column("weekly_report_id", sa.String(length=26), nullable=False),
        sa.Column("daily_report_day_id", sa.String(length=26), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("included_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["daily_report_day_id"], ["daily_report_days.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["weekly_report_id"], ["weekly_reports.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("weekly_report_id", "daily_report_day_id"),
    )
    op.create_index(
        "ix_weekly_sources_daily_day",
        "weekly_report_sources",
        ["daily_report_day_id"],
        unique=False,
    )
    op.execute(
        """
        INSERT INTO weekly_report_sources (
            weekly_report_id, daily_report_day_id, work_date, included_at
        )
        SELECT weekly_report_id, daily_report_id, work_date, included_at
        FROM weekly_report_sources_v1_data
        """
    )
    op.drop_table("weekly_report_sources_v1_data")


def _rebuild_user_settings_without_auto_archive() -> None:
    op.create_table(
        "user_settings_v2",
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("timezone", sa.String(length=64), server_default="Asia/Shanghai", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.execute(
        """
        INSERT INTO user_settings_v2 (user_id, timezone, created_at, updated_at)
        SELECT user_id, timezone, created_at, updated_at FROM user_settings
        """
    )
    op.drop_table("user_settings")
    op.rename_table("user_settings_v2", "user_settings")


def _create_admin_audit_events() -> None:
    op.create_table(
        "admin_audit_events",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("actor_user_id", sa.String(length=26), nullable=True),
        sa.Column("actor_username_snapshot", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("target_owner_id", sa.String(length=26), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "action IN ('daily_submission_revoked', 'user_deleted')",
            name="ck_admin_audit_events_action",
        ),
        sa.CheckConstraint(
            "length(trim(reason)) BETWEEN 1 AND 500",
            name="ck_admin_audit_events_reason_length",
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_audit_action_created",
        "admin_audit_events",
        ["action", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_admin_audit_target_created",
        "admin_audit_events",
        ["target_id", sa.text("created_at DESC")],
        unique=False,
    )


def _table_count(connection: Connection, table: str) -> int:
    return int(connection.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar_one())


def _verify_upgrade(
    connection: Connection,
    *,
    daily_count: int,
    archived_count: int,
    weekly_source_count: int,
) -> None:
    if _table_count(connection, "daily_report_days") != daily_count:
        raise RuntimeError("daily report day count changed during migration")
    if _table_count(connection, "daily_reports") != daily_count:
        raise RuntimeError("daily report entry count changed during migration")
    migrated_archived = int(
        connection.execute(
            sa.text("SELECT COUNT(*) FROM daily_report_days WHERE status = 'archived'")
        ).scalar_one()
    )
    if migrated_archived != archived_count:
        raise RuntimeError("archived daily report count changed during migration")
    if _table_count(connection, "weekly_report_sources") != weekly_source_count:
        raise RuntimeError("weekly report source count changed during migration")
    if connection.exec_driver_sql("PRAGMA foreign_key_check").first() is not None:
        raise RuntimeError("foreign key violation detected after migration")


def _preflight_v1_weekly_json(connection: Connection) -> None:
    weekly_rows = connection.execute(
        sa.text(
            """
            SELECT id, generated_content_json, content_json, source_snapshot_json
            FROM weekly_reports ORDER BY id
            """
        )
    ).mappings()
    for weekly in weekly_rows:
        weekly_id = str(weekly["id"])
        source_ids: set[str] = set()
        for column in ("generated_content_json", "content_json"):
            value = _load_weekly_json(weekly[column], weekly_id=weekly_id, column=column)
            if not isinstance(value, dict) or not isinstance(value.get("days"), list):
                raise RuntimeError(
                    f"cannot migrate weekly report {weekly_id}: invalid {column} shape"
                )
            for day in value["days"]:
                if (
                    not isinstance(day, dict)
                    or not isinstance(day.get("daily_report_id"), str)
                    or not isinstance(day.get("fields"), list)
                ):
                    raise RuntimeError(
                        f"cannot migrate weekly report {weekly_id}: invalid {column} day"
                    )
                source_ids.add(str(day["daily_report_id"]))
        source_snapshot = _load_weekly_json(
            weekly["source_snapshot_json"],
            weekly_id=weekly_id,
            column="source_snapshot_json",
        )
        if not isinstance(source_snapshot, list):
            raise RuntimeError(
                f"cannot migrate weekly report {weekly_id}: invalid source snapshot shape"
            )
        for day in source_snapshot:
            if not isinstance(day, dict) or not isinstance(day.get("daily_report_id"), str):
                raise RuntimeError(
                    f"cannot migrate weekly report {weekly_id}: invalid source snapshot day"
                )
            source_ids.add(str(day["daily_report_id"]))
        for daily_report_id in source_ids:
            source = connection.execute(
                sa.text(
                    """
                    SELECT submitted_at FROM daily_reports
                    WHERE id = :daily_report_id
                    """
                ),
                {"daily_report_id": daily_report_id},
            ).first()
            if source is None or source[0] is None:
                raise RuntimeError(
                    f"cannot migrate weekly report {weekly_id}: source report is missing"
                )


def upgrade() -> None:
    connection = op.get_bind()
    _preflight_v1_weekly_json(connection)
    daily_count = _table_count(connection, "daily_reports")
    archived_count = int(
        connection.execute(
            sa.text("SELECT COUNT(*) FROM daily_reports WHERE status = 'archived'")
        ).scalar_one()
    )
    weekly_source_count = _table_count(connection, "weekly_report_sources")
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), server_default="0", nullable=False),
    )
    _create_daily_report_days(connection)
    _rebuild_daily_reports()
    _upgrade_weekly_json(connection)
    _rebuild_user_settings_without_auto_archive()
    _create_admin_audit_events()
    _verify_upgrade(
        connection,
        daily_count=daily_count,
        archived_count=archived_count,
        weekly_source_count=weekly_source_count,
    )


def _single_weekly_entry(
    day: object, *, weekly_id: str, column: str
) -> tuple[dict[str, object], dict[str, object]]:
    if not isinstance(day, dict) or not isinstance(day.get("entries"), list):
        raise RuntimeError(f"cannot downgrade weekly report {weekly_id}: invalid {column} day")
    entries = day["entries"]
    if day.get("source_count") != 1 or len(entries) != 1:
        raise RuntimeError(f"cannot downgrade weekly report {weekly_id}: multiple source entries")
    entry = entries[0]
    if (
        not isinstance(entry, dict)
        or not isinstance(entry.get("daily_report_id"), str)
        or day.get("daily_report_day_id") != entry["daily_report_id"]
    ):
        raise RuntimeError(
            f"cannot downgrade weekly report {weekly_id}: source mapping is not lossless"
        )
    return day, entry


def _downgrade_weekly_content(*, weekly_id: str, column: str, raw: object) -> str:
    value = _load_weekly_json(raw, weekly_id=weekly_id, column=column)
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != 2
        or not isinstance(value.get("days"), list)
    ):
        raise RuntimeError(f"cannot downgrade weekly report {weekly_id}: invalid {column} shape")
    old_days: list[dict[str, object]] = []
    for candidate in value["days"]:
        day, entry = _single_weekly_entry(candidate, weekly_id=weekly_id, column=column)
        if not isinstance(entry.get("fields"), list):
            raise RuntimeError(
                f"cannot downgrade weekly report {weekly_id}: invalid {column} fields"
            )
        old_days.append(
            {
                "work_date": day.get("work_date"),
                "daily_report_id": entry["daily_report_id"],
                "fields": entry["fields"],
            }
        )
    old_value = {
        "days": old_days,
        "supplement": value.get("supplement", ""),
        "next_week_plan": value.get("next_week_plan", ""),
        "risks": value.get("risks", ""),
    }
    if not all(
        isinstance(old_value[key], str) for key in ("supplement", "next_week_plan", "risks")
    ):
        raise RuntimeError(f"cannot downgrade weekly report {weekly_id}: invalid free-text field")
    return json.dumps(old_value, ensure_ascii=False, separators=(",", ":"))


def _downgrade_weekly_source_snapshot(*, weekly_id: str, raw: object) -> str:
    value = _load_weekly_json(raw, weekly_id=weekly_id, column="source_snapshot_json")
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != 2
        or not isinstance(value.get("days"), list)
    ):
        raise RuntimeError(
            f"cannot downgrade weekly report {weekly_id}: invalid source snapshot shape"
        )
    old_days: list[dict[str, object]] = []
    for candidate in value["days"]:
        day, entry = _single_weekly_entry(
            candidate,
            weekly_id=weekly_id,
            column="source_snapshot_json",
        )
        old_days.append(
            {
                "daily_report_id": entry["daily_report_id"],
                "work_date": day.get("work_date"),
            }
        )
    return json.dumps(old_days, ensure_ascii=False, separators=(",", ":"))


def _downgrade_weekly_json(connection: Connection) -> None:
    rows = list(
        connection.execute(
            sa.text(
                """
                SELECT id, generated_content_json, content_json, source_snapshot_json
                FROM weekly_reports ORDER BY id
                """
            )
        ).mappings()
    )
    payloads: list[dict[str, str]] = []
    for row in rows:
        weekly_id = str(row["id"])
        payloads.append(
            {
                "id": weekly_id,
                "generated_content_json": _downgrade_weekly_content(
                    weekly_id=weekly_id,
                    column="generated_content_json",
                    raw=row["generated_content_json"],
                ),
                "content_json": _downgrade_weekly_content(
                    weekly_id=weekly_id,
                    column="content_json",
                    raw=row["content_json"],
                ),
                "source_snapshot_json": _downgrade_weekly_source_snapshot(
                    weekly_id=weekly_id,
                    raw=row["source_snapshot_json"],
                ),
            }
        )
    update_weekly = sa.text(
        """
        UPDATE weekly_reports
        SET generated_content_json = :generated_content_json,
            content_json = :content_json,
            source_snapshot_json = :source_snapshot_json
        WHERE id = :id
        """
    )
    for payload in payloads:
        connection.execute(update_weekly, payload)


def _assert_downgrade_is_lossless(connection: Connection) -> None:
    row = connection.execute(
        sa.text(
            """
            SELECT day_id, COUNT(*) AS report_count
            FROM daily_reports
            GROUP BY day_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if row is not None:
        raise RuntimeError(
            "cannot downgrade: at least one work date contains multiple daily report entries"
        )
    if _table_count(connection, "admin_audit_events") > 0:
        raise RuntimeError("cannot downgrade: administrator audit events would be lost")


def _restore_v1_daily_reports() -> None:
    op.execute(
        """
        CREATE TABLE weekly_report_sources_v2_data AS
        SELECT source.weekly_report_id,
               report.id AS daily_report_id,
               source.work_date,
               source.included_at
        FROM weekly_report_sources AS source
        JOIN daily_reports AS report
          ON report.day_id = source.daily_report_day_id
        """
    )
    op.drop_table("weekly_report_sources")

    op.create_table(
        "daily_reports_v1",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("template_version_id", sa.String(length=26), nullable=False),
        sa.Column("template_snapshot_json", sa.Text(), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'submitted', 'archived')", name="ck_daily_reports_status"
        ),
        sa.CheckConstraint(
            "(status != 'draft' OR archived_at IS NULL) AND "
            "(status != 'archived' OR (submitted_at IS NOT NULL AND archived_at IS NOT NULL))",
            name="ck_daily_reports_status_timestamps",
        ),
        sa.ForeignKeyConstraint(
            ["template_version_id"], ["template_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "work_date", name="uq_daily_reports_user_work_date"),
    )
    op.execute(
        """
        INSERT INTO daily_reports_v1 (
            id, user_id, work_date, status, template_version_id,
            template_snapshot_json, content_json, version, submitted_at,
            archived_at, created_at, updated_at
        )
        SELECT report.id, day.user_id, day.work_date, report.status,
               report.template_version_id, report.template_snapshot_json,
               report.content_json, report.version, report.submitted_at,
               report.archived_at, report.created_at, report.updated_at
        FROM daily_reports AS report
        JOIN daily_report_days AS day ON day.id = report.day_id
        """
    )
    op.drop_table("daily_reports")
    op.rename_table("daily_reports_v1", "daily_reports")
    op.create_index(
        "ix_daily_reports_user_date",
        "daily_reports",
        ["user_id", sa.text("work_date DESC"), sa.text("id DESC")],
        unique=False,
    )
    op.create_index(
        "ix_daily_reports_user_status_date",
        "daily_reports",
        ["user_id", "status", sa.text("work_date DESC")],
        unique=False,
    )

    op.create_table(
        "weekly_report_sources",
        sa.Column("weekly_report_id", sa.String(length=26), nullable=False),
        sa.Column("daily_report_id", sa.String(length=26), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("included_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["daily_report_id"], ["daily_reports.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["weekly_report_id"], ["weekly_reports.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("weekly_report_id", "daily_report_id"),
    )
    op.create_index(
        "ix_weekly_sources_daily",
        "weekly_report_sources",
        ["daily_report_id"],
        unique=False,
    )
    op.execute(
        """
        INSERT INTO weekly_report_sources (
            weekly_report_id, daily_report_id, work_date, included_at
        )
        SELECT weekly_report_id, daily_report_id, work_date, included_at
        FROM weekly_report_sources_v2_data
        """
    )
    op.drop_table("weekly_report_sources_v2_data")
    op.drop_table("daily_report_days")


def _restore_v1_user_settings() -> None:
    op.create_table(
        "user_settings_v1",
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("auto_archive_on_submit", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("timezone", sa.String(length=64), server_default="Asia/Shanghai", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.execute(
        """
        INSERT INTO user_settings_v1 (
            user_id, auto_archive_on_submit, timezone, created_at, updated_at
        )
        SELECT user_id, 0, timezone, created_at, updated_at FROM user_settings
        """
    )
    op.drop_table("user_settings")
    op.rename_table("user_settings_v1", "user_settings")


def downgrade() -> None:
    connection = op.get_bind()
    _assert_downgrade_is_lossless(connection)
    _downgrade_weekly_json(connection)
    op.drop_table("admin_audit_events")
    _restore_v1_daily_reports()
    _restore_v1_user_settings()
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("must_change_password")
