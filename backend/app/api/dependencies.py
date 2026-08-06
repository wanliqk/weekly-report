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
