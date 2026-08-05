from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserSettings


class UserSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, settings: UserSettings) -> None:
        self._session.add(settings)
        await self._session.flush()

    async def get_for_owner(self, owner_id: str) -> UserSettings | None:
        result = await self._session.execute(
            select(UserSettings).where(UserSettings.user_id == owner_id)
        )
        return result.scalar_one_or_none()

    async def update_auto_archive(
        self, owner_id: str, *, enabled: bool, updated_at: datetime
    ) -> bool:
        result = await self._session.execute(
            update(UserSettings)
            .where(UserSettings.user_id == owner_id)
            .values(auto_archive_on_submit=enabled, updated_at=updated_at)
        )
        return bool(result.rowcount == 1)
