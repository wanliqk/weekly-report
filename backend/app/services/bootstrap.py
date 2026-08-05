from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, utc_now
from app.core.errors import AppError
from app.core.security import hash_password
from app.core.ulid import generate_ulid
from app.models import User
from app.repositories.user import UserRepository
from app.services.user import create_default_user_resources, normalize_username

ALREADY_INITIALIZED_CODE = 40001


class AlreadyInitializedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code=ALREADY_INITIALIZED_CODE,
            http_status=400,
            message="系统已完成初始化 无法重复创建管理员",
        )


class BootstrapService:
    """First-admin init: user + settings + template + version in one transaction."""

    def __init__(self, session: AsyncSession, *, clock: Clock = utc_now) -> None:
        self._session = session
        self._clock = clock
        self._users = UserRepository(session)

    async def is_initialized(self) -> bool:
        return await self._users.any_exists()

    async def bootstrap_admin(self, *, username: str, password: str, display_name: str) -> User:
        user = User(
            id=generate_ulid(),
            username=username.strip(),
            username_normalized=normalize_username(username),
            display_name=display_name.strip(),
            password_hash=hash_password(password),
            role="admin",
            password_changed_at=self._clock(),
        )
        inserted = await self._users.create_if_no_users_exist(user)
        if not inserted:
            raise AlreadyInitializedError()

        # The row above was written via a raw Core insert (bypassing
        # `session.add`), so `user` never picked up the columns SQLite
        # filled in via table DEFAULTs (token_version/is_active/timestamps).
        # Re-fetch through the session so the returned instance reflects the
        # real persisted row and is properly identity-mapped.
        refreshed_user = await self._users.get_by_id(user.id)
        assert refreshed_user is not None
        user = refreshed_user

        await create_default_user_resources(self._session, user_id=user.id)

        await self._session.commit()
        return user
