from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserSettings


class UserSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, settings: UserSettings) -> None:
        self._session.add(settings)
        await self._session.flush()
