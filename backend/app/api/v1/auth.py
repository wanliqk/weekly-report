from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_authenticated_user, get_jwt_secret
from app.db.session import get_db_session
from app.models import User
from app.schemas.auth import (
    ChangePasswordRequest,
    EmptyData,
    LoginData,
    LoginRequest,
    MeData,
)
from app.schemas.common import ApiResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=ApiResponse[LoginData])
async def login(
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    jwt_secret: Annotated[str, Depends(get_jwt_secret)],
) -> ApiResponse[LoginData]:
    result = await AuthService(session, jwt_secret=jwt_secret).login(
        username=payload.username, password=payload.password
    )
    return ApiResponse(
        data=LoginData(access_token=result.access_token, expires_at=result.expires_at)
    )


@router.get("/me", response_model=ApiResponse[MeData])
async def me(
    current_user: Annotated[User, Depends(get_authenticated_user)],
) -> ApiResponse[MeData]:
    return ApiResponse(data=MeData.model_validate(current_user))


@router.put("/password", response_model=ApiResponse[EmptyData])
async def change_password(
    payload: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_authenticated_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    jwt_secret: Annotated[str, Depends(get_jwt_secret)],
) -> ApiResponse[EmptyData]:
    await AuthService(session, jwt_secret=jwt_secret).change_password(
        current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return ApiResponse(data=EmptyData())


@router.post("/logout", response_model=ApiResponse[EmptyData])
async def logout(
    _current_user: Annotated[User, Depends(get_authenticated_user)],
) -> ApiResponse[EmptyData]:
    return ApiResponse(data=EmptyData())
