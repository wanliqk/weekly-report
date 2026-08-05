from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, utc_now
from app.core.errors import AppError
from app.models import UserSettings
from app.repositories.user_settings import UserSettingsRepository


class SettingsNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40401, http_status=404, message="用户设置不存在")


class SettingsService:
    def __init__(self, session: AsyncSession, *, clock: Clock = utc_now) -> None:
        self._session = session
        self._clock = clock
        self._settings = UserSettingsRepository(session)

    async def get(self, owner_id: str) -> UserSettings:
        settings = await self._settings.get_for_owner(owner_id)
        if settings is None:
            raise SettingsNotFoundError()
        return settings

    async def update_auto_archive(self, owner_id: str, *, enabled: bool) -> UserSettings:
        updated = await self._settings.update_auto_archive(
            owner_id, enabled=enabled, updated_at=self._clock()
        )
        if not updated:
            raise SettingsNotFoundError()
        await self._session.commit()
        return await self.get(owner_id)
