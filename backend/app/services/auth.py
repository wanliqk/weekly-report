from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_token import (
    InvalidAccessTokenError,
    decode_access_token,
    encode_access_token,
)
from app.core.clock import Clock, utc_now
from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.models import User
from app.repositories.user import UserRepository
from app.services.user import normalize_username

INVALID_CREDENTIALS_CODE = 40101
TOKEN_INVALID_CODE = 40102
_DUMMY_PASSWORD_HASH = hash_password("timing-only-password-placeholder")


class InvalidCredentialsError(AppError):
    def __init__(self) -> None:
        super().__init__(code=INVALID_CREDENTIALS_CODE, http_status=401, message="用户名或密码错误")


class IncorrectCurrentPasswordError(AppError):
    """Same public code as a failed login (40101): both mean "you did not prove who you are"."""

    def __init__(self) -> None:
        super().__init__(code=INVALID_CREDENTIALS_CODE, http_status=401, message="当前密码不正确")


class TokenInvalidError(AppError):
    def __init__(self) -> None:
        super().__init__(code=TOKEN_INVALID_CODE, http_status=401, message="Token 无效或已过期")


@dataclass(frozen=True)
class LoginResult:
    user: User
    access_token: str
    expires_at: datetime


class AuthService:
    def __init__(self, session: AsyncSession, *, jwt_secret: str, clock: Clock = utc_now) -> None:
        self._session = session
        self._jwt_secret = jwt_secret
        self._clock = clock
        self._users = UserRepository(session)

    async def login(self, *, username: str, password: str) -> LoginResult:
        user = await self._users.get_by_username_normalized(normalize_username(username))
        # Same generic failure for "no such user", "wrong password", and
        # "disabled" so a login attempt cannot be used to enumerate accounts.
        password_hash = user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
        password_matches = verify_password(password=password, password_hash=password_hash)
        if user is None or not user.is_active or not password_matches:
            raise InvalidCredentialsError()

        encoded = encode_access_token(
            user_id=user.id,
            role=user.role,
            token_version=user.token_version,
            secret=self._jwt_secret,
            clock=self._clock,
        )
        return LoginResult(user=user, access_token=encoded.token, expires_at=encoded.expires_at)

    async def authenticate_token(self, token: str) -> User:
        try:
            claims = decode_access_token(token, secret=self._jwt_secret)
        except InvalidAccessTokenError as error:
            raise TokenInvalidError() from error

        user = await self._users.get_by_id(claims.user_id)
        if (
            user is None
            or not user.is_active
            or user.token_version != claims.token_version
            or user.role != claims.role
        ):
            raise TokenInvalidError()
        return user

    async def change_password(
        self, user: User, *, current_password: str, new_password: str
    ) -> None:
        if not verify_password(password=current_password, password_hash=user.password_hash):
            raise IncorrectCurrentPasswordError()

        await self._users.update_password(
            user.id,
            password_hash=hash_password(new_password),
            password_changed_at=self._clock(),
            must_change_password=False,
        )
        await self._session.commit()
