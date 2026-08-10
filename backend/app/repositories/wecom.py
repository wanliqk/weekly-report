from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DailyReportDay, WeComDailySyncRecord, WeComSyncProfile, WeComUserBinding


class WeComUserBindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, binding: WeComUserBinding) -> None:
        self._session.add(binding)
        await self._session.flush()

    async def get_for_owner(self, owner_id: str) -> WeComUserBinding | None:
        result = await self._session.execute(
            select(WeComUserBinding).where(WeComUserBinding.user_id == owner_id)
        )
        return result.scalar_one_or_none()


class WeComSyncProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, profile: WeComSyncProfile) -> None:
        self._session.add(profile)
        await self._session.flush()

    async def get_for_owner(self, owner_id: str) -> WeComSyncProfile | None:
        result = await self._session.execute(
            select(WeComSyncProfile).where(WeComSyncProfile.user_id == owner_id)
        )
        return result.scalar_one_or_none()

    async def update_field_mapping_if_version(
        self,
        *,
        owner_id: str,
        expected_version: int,
        field_mapping_json: str,
        updated_at: datetime,
    ) -> bool:
        """Conditional update for `PUT /api/v1/wecom/profile` (WECOM-06).

        Only `field_mapping_json` is ever written here — the only column a
        user is meant to adjust after connecting.
        `question_mapping_json`/`schema_fingerprint`/`destination_fingerprint`
        stay whatever connect-time discovery produced, and `recipient_config_json`
        is never user-editable at all (`ai-docs/decisions.md` `PROD-032`) — it
        is only ever written by `WeComConnectionService._upsert_profile()` at
        connect/reconnect time. Mirrors the
        `update(...).where(..., version == expected)` + `rowcount` idiom used
        throughout `app/repositories/daily_report.py`.
        """
        result = await self._session.execute(
            update(WeComSyncProfile)
            .where(
                WeComSyncProfile.user_id == owner_id,
                WeComSyncProfile.version == expected_version,
            )
            .values(
                field_mapping_json=field_mapping_json,
                version=WeComSyncProfile.version + 1,
                updated_at=updated_at,
            )
        )
        return bool(result.rowcount == 1)


class WeComDailySyncRecordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: WeComDailySyncRecord) -> None:
        self._session.add(record)
        await self._session.flush()

    async def get_for_owner(self, record_id: str, owner_id: str) -> WeComDailySyncRecord | None:
        result = await self._session.execute(
            select(WeComDailySyncRecord).where(
                WeComDailySyncRecord.id == record_id,
                WeComDailySyncRecord.user_id == owner_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_for_owner_by_day_and_destination(
        self, *, owner_id: str, daily_report_day_id: str, destination_fingerprint: str
    ) -> WeComDailySyncRecord | None:
        result = await self._session.execute(
            select(WeComDailySyncRecord).where(
                WeComDailySyncRecord.user_id == owner_id,
                WeComDailySyncRecord.daily_report_day_id == daily_report_day_id,
                WeComDailySyncRecord.destination_fingerprint == destination_fingerprint,
            )
        )
        return result.scalar_one_or_none()

    async def list_page_for_owner(
        self,
        owner_id: str,
        *,
        status: str | None,
        date_from: date | None,
        date_to: date | None,
        page: int,
        page_size: int,
    ) -> tuple[list[tuple[WeComDailySyncRecord, date]], int]:
        """Returns `(record, work_date)` pairs — the record itself doesn't
        carry `work_date`, only `daily_report_day_id`, so every list/filter
        query joins `daily_report_days` to expose and filter on it."""
        filters = [WeComDailySyncRecord.user_id == owner_id]
        if status is not None:
            filters.append(WeComDailySyncRecord.status == status)
        if date_from is not None:
            filters.append(DailyReportDay.work_date >= date_from)
        if date_to is not None:
            filters.append(DailyReportDay.work_date <= date_to)

        base = select(WeComDailySyncRecord, DailyReportDay.work_date).join(
            DailyReportDay, WeComDailySyncRecord.daily_report_day_id == DailyReportDay.id
        )
        total_result = await self._session.execute(
            select(func.count())
            .select_from(WeComDailySyncRecord)
            .join(DailyReportDay, WeComDailySyncRecord.daily_report_day_id == DailyReportDay.id)
            .where(*filters)
        )
        total = total_result.scalar_one()

        items_result = await self._session.execute(
            base.where(*filters)
            .order_by(WeComDailySyncRecord.updated_at.desc(), WeComDailySyncRecord.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = [(row[0], row[1]) for row in items_result.all()]
        return items, total

    async def transition_to_syncing(
        self,
        *,
        record_id: str,
        owner_id: str,
        allowed_statuses: Sequence[str],
        attempt_token: str,
        now: datetime,
    ) -> bool:
        """Step 1 of the two-short-transactions state machine
        (`docs/方案设计.md` §3.2): condition on the record's *current* status
        being one of `allowed_statuses`, atomically move it to `syncing`,
        bump `attempt_count`, and mint a fresh `attempt_token`. A `rowcount`
        of 0 means a concurrent request already changed the status (or it
        was never in an executable state) — the caller must not proceed to
        call the remote Client in that case.
        """
        result = await self._session.execute(
            update(WeComDailySyncRecord)
            .where(
                WeComDailySyncRecord.id == record_id,
                WeComDailySyncRecord.user_id == owner_id,
                WeComDailySyncRecord.status.in_(allowed_statuses),
            )
            .values(
                status="syncing",
                attempt_token=attempt_token,
                attempt_count=WeComDailySyncRecord.attempt_count + 1,
                last_attempt_at=now,
                updated_at=now,
            )
        )
        return bool(result.rowcount == 1)

    async def finalize_attempt(
        self,
        *,
        record_id: str,
        owner_id: str,
        attempt_token: str,
        status: str,
        now: datetime,
        profile_id: str,
        profile_version: int,
        payload_fingerprint: str,
        remote_answer_id: str | None,
        remote_reply_id: str | None,
        remote_journal_uuid: str | None,
        last_error_kind: str | None,
        last_error_message: str | None,
        succeeded_at: datetime | None,
    ) -> bool:
        """Step 3 of the state machine: writes the final outcome only if
        `record_id + attempt_token + status == 'syncing'` still all match —
        a late/duplicate response from a superseded attempt (whose token no
        longer matches the row) is silently discarded rather than
        overwriting a newer attempt's result (`docs/方案设计.md` §3.2 point 3).
        """
        result = await self._session.execute(
            update(WeComDailySyncRecord)
            .where(
                WeComDailySyncRecord.id == record_id,
                WeComDailySyncRecord.user_id == owner_id,
                WeComDailySyncRecord.attempt_token == attempt_token,
                WeComDailySyncRecord.status == "syncing",
            )
            .values(
                status=status,
                attempt_token=None,
                profile_id=profile_id,
                profile_version=profile_version,
                payload_fingerprint=payload_fingerprint,
                remote_answer_id=remote_answer_id,
                remote_reply_id=remote_reply_id,
                remote_journal_uuid=remote_journal_uuid,
                last_error_kind=last_error_kind,
                last_error_message=last_error_message,
                last_attempt_at=now,
                succeeded_at=succeeded_at,
                updated_at=now,
            )
        )
        return bool(result.rowcount == 1)

    async def transition_to_pending_for_retry(
        self,
        *,
        record_id: str,
        owner_id: str,
        allowed_statuses: Sequence[str],
        now: datetime,
    ) -> bool:
        """`POST /api/v1/wecom/sync-records/{record_id}/retry`: only
        re-queues (`attempt_count` is untouched — it only increments when a
        record actually enters `syncing`, per the task's retry semantics).
        """
        result = await self._session.execute(
            update(WeComDailySyncRecord)
            .where(
                WeComDailySyncRecord.id == record_id,
                WeComDailySyncRecord.user_id == owner_id,
                WeComDailySyncRecord.status.in_(allowed_statuses),
            )
            .values(status="pending", attempt_token=None, updated_at=now)
        )
        return bool(result.rowcount == 1)

    async def recover_stale_syncing(self, *, cutoff: datetime, now: datetime) -> int:
        """`docs/方案设计.md` §10.3: "启动恢复时,超过合理租约仍为 syncing 的记录转
        uncertain,绝不直接转 failed" — a record still `syncing` past a reasonable
        lease was interrupted mid-flight (process crash before the finalize
        short transaction ever ran), so whether the remote call was received
        is genuinely unknown; only remote reconciliation (a future `execute()`
        call) may resolve it, matching the same rule already applied to any
        other `uncertain` record. Not owner-scoped — this is a maintenance
        sweep across every user, like `ExportService.cleanup_expired()`.
        """
        result = await self._session.execute(
            update(WeComDailySyncRecord)
            .where(
                WeComDailySyncRecord.status == "syncing",
                or_(
                    WeComDailySyncRecord.last_attempt_at.is_(None),
                    WeComDailySyncRecord.last_attempt_at <= cutoff,
                ),
            )
            .values(status="uncertain", attempt_token=None, updated_at=now)
        )
        return int(result.rowcount)
