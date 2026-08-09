from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, utc_now
from app.core.errors import AppError
from app.core.security import hash_password
from app.core.ulid import generate_ulid
from app.models import User
from app.repositories.user import UserRepository
from app.services.user import create_default_user_resources, normalize_username

ALREADY_INITIALIZED_CODE = 40001
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_DISPLAY_NAME = "系统管理员"
DEFAULT_ADMIN_PASSWORD = "admin123"


class AlreadyInitializedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code=ALREADY_INITIALIZED_CODE,
            http_status=400,
            message="系统已完成初始化 无法重复创建账号",
        )


class ReservedBootstrapUsernameError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code=40001,
            http_status=400,
            message="首次用户不能使用系统管理员用户名 admin",
        )


class BootstrapService:
    """Atomically creates the first ordinary user and the fixed admin account."""

    def __init__(self, session: AsyncSession, *, clock: Clock = utc_now) -> None:
        self._session = session
        self._clock = clock
        self._users = UserRepository(session)

    async def is_initialized(self) -> bool:
        return await self._users.any_exists()

    async def bootstrap(self, *, username: str, password: str, display_name: str) -> User:
        username_normalized = normalize_username(username)
        if username_normalized == DEFAULT_ADMIN_USERNAME:
            raise ReservedBootstrapUsernameError()

        now = self._clock()
        user = User(
            id=generate_ulid(),
            username=username.strip(),
            username_normalized=username_normalized,
            display_name=display_name.strip(),
            password_hash=hash_password(password),
            role="user",
            must_change_password=False,
            password_changed_at=now,
        )
        inserted = await self._users.create_first_user_if_empty(user)
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

        admin = User(
            id=generate_ulid(),
            username=DEFAULT_ADMIN_USERNAME,
            username_normalized=DEFAULT_ADMIN_USERNAME,
            display_name=DEFAULT_ADMIN_DISPLAY_NAME,
            password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
            role="admin",
            must_change_password=True,
            password_changed_at=now,
        )
        await self._users.add(admin)
        await create_default_user_resources(self._session, user_id=user.id)
        await create_default_user_resources(self._session, user_id=admin.id)

        await self._session.commit()
        return user
