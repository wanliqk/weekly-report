from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin
from app.db.session import get_db_session
from app.models import User
from app.schemas.common import ApiResponse
from app.schemas.user import (
    PasswordResetRequest,
    UserCreateRequest,
    UserData,
    UserListData,
    UserUpdateRequest,
)
from app.services.user import UserService

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=ApiResponse[UserListData])
async def list_users(
    _admin: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[UserListData]:
    items, total = await UserService(session).list_users(page=page, page_size=page_size)
    return ApiResponse(
        data=UserListData(
            items=[UserData.model_validate(item) for item in items],
            page=page,
            page_size=page_size,
            total=total,
        )
    )


@router.post("", response_model=ApiResponse[UserData])
async def create_user(
    payload: UserCreateRequest,
    _admin: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[UserData]:
    user = await UserService(session).create_user(
        username=payload.username,
        password=payload.password,
        display_name=payload.display_name,
        role=payload.role,
    )
    return ApiResponse(data=UserData.model_validate(user))


@router.get("/{user_id}", response_model=ApiResponse[UserData])
async def get_user(
    user_id: str,
    _admin: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[UserData]:
    user = await UserService(session).get_user(user_id)
    return ApiResponse(data=UserData.model_validate(user))


@router.patch("/{user_id}", response_model=ApiResponse[UserData])
async def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    _admin: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[UserData]:
    user = await UserService(session).update_user(
        user_id,
        display_name=payload.display_name,
        role=payload.role,
        is_active=payload.is_active,
    )
    return ApiResponse(data=UserData.model_validate(user))


@router.put("/{user_id}/password", response_model=ApiResponse[UserData])
async def reset_password(
    user_id: str,
    payload: PasswordResetRequest,
    _admin: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[UserData]:
    user = await UserService(session).reset_password(user_id, new_password=payload.new_password)
    return ApiResponse(data=UserData.model_validate(user))
