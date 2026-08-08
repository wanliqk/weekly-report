from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WeComDailySyncRecord, WeComSyncProfile, WeComUserBinding


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
