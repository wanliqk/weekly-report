from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin
from app.db.session import get_db_session
from app.models import User
from app.schemas.auth import EmptyData
from app.schemas.common import ApiResponse
from app.schemas.user import (
    PasswordResetRequest,
    UserCreateRequest,
    UserData,
    UserDeleteRequest,
    UserListData,
    UserUpdateRequest,
)
from app.services.user import UserService

router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _with_deletion_eligibility(user: User, reason: str | None) -> UserData:
    data = UserData.model_validate(user)
    return data.model_copy(update={"can_delete": reason is None, "cannot_delete_reason": reason})


@router.get("", response_model=ApiResponse[UserListData])
async def list_users(
    admin: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[UserListData]:
    service = UserService(session)
    items, total = await service.list_users(page=page, page_size=page_size)
    reasons = await service.deletion_eligibility(items, actor_id=admin.id)
    return ApiResponse(
        data=UserListData(
            items=[_with_deletion_eligibility(item, reasons[item.id]) for item in items],
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
    admin: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[UserData]:
    service = UserService(session)
    user = await service.get_user(user_id)
    reasons = await service.deletion_eligibility([user], actor_id=admin.id)
    return ApiResponse(data=_with_deletion_eligibility(user, reasons[user.id]))


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


@router.delete("/{user_id}", response_model=ApiResponse[EmptyData])
async def delete_user(
    user_id: str,
    payload: UserDeleteRequest,
    admin: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[EmptyData]:
    await UserService(session).delete_user(
        admin,
        user_id,
        confirm_username=payload.confirm_username,
        reason=payload.reason,
    )
    return ApiResponse(data=EmptyData())
