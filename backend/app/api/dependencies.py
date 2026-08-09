import secrets
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.backup_registry import BackupRegistry
from app.core.config import Settings
from app.core.errors import AppError
from app.db.session import get_db_session
from app.models import User
from app.services.auth import AuthService, TokenInvalidError

_bearer = HTTPBearer(auto_error=False)

# SEC-014 (`docs/方案设计.md` §3.1/§9.2): distinct from `X-Runtime-Secret` and
# distinct from the runtime-secret failure code `40103` on purpose — a
# missing/invalid Main-only bridge secret is a different failure mode (only
# Electron Main is ever supposed to hold this value) and must not be
# reported the same way as a renderer forgetting the ordinary runtime
# header. Not part of the frozen `docs/方案设计.md` §9.4 error code table,
# which only lists *sync business* errors; this is a general auth failure,
# same category as the existing 401 codes.
MAIN_BRIDGE_SECRET_HEADER = "X-Main-Bridge-Secret"
MAIN_BRIDGE_SECRET_INVALID_CODE = 40104


def get_jwt_secret(request: Request) -> str:
    secret: str = request.app.state.jwt_secret
    return secret


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_backup_registry(request: Request) -> BackupRegistry:
    registry: BackupRegistry = request.app.state.backup_registry
    return registry


async def get_authenticated_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    jwt_secret: Annotated[str, Depends(get_jwt_secret)],
) -> User:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise TokenInvalidError()
    return await AuthService(session, jwt_secret=jwt_secret).authenticate_token(
        credentials.credentials
    )


async def get_current_user(
    current_user: Annotated[User, Depends(get_authenticated_user)],
) -> User:
    if current_user.must_change_password:
        raise AppError(code=40303, http_status=403, message="请先修改临时密码")
    return current_user


async def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role != "admin":
        raise AppError(code=40301, http_status=403, message="角色权限不足")
    return current_user


async def require_main_bridge_secret(
    request: Request,
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> None:
    """Gates `/api/v1/internal/wecom/**` (WECOM-06). Applied at router level
    via `dependencies=[Depends(require_main_bridge_secret)]` so it runs
    before any handler; each handler still separately depends on
    `get_current_user` — a Main-only request is still made *as* a specific
    logged-in user, this is an additional layer, not a replacement for JWT
    auth (`docs/方案设计.md` §3.1: "同时校验当前用户 JWT 与 X-Main-Bridge-Secret")."""
    supplied_secret = request.headers.get(MAIN_BRIDGE_SECRET_HEADER, "")
    expected_secret = settings.main_bridge_secret
    if expected_secret is None or not secrets.compare_digest(supplied_secret, expected_secret):
        raise AppError(
            code=MAIN_BRIDGE_SECRET_INVALID_CODE,
            http_status=401,
            message="内部服务密钥缺失或无效",
        )
