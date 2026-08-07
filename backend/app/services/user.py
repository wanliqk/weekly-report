import json
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, utc_now
from app.core.errors import AppError
from app.core.security import hash_password
from app.core.ulid import generate_ulid
from app.models import AdminAuditEvent, ReportTemplate, TemplateVersion, User, UserSettings
from app.repositories.admin_audit import AdminAuditRepository
from app.repositories.template import TemplateRepository
from app.repositories.user import UserRepository
from app.repositories.user_settings import UserSettingsRepository

_USER_DELETED_ACTION = "user_deleted"

DEFAULT_TEMPLATE_NAME = "日报模板"


class UsernameAlreadyExistsError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40001, http_status=400, message="用户名已存在")


class UserNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40401, http_status=404, message="用户不存在")


class LastActiveAdminError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40001, http_status=400, message="不能禁用或降级最后一个有效管理员")


class CannotDeleteSelfError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40001, http_status=400, message="不能删除当前登录账号")


class UsernameConfirmationMismatchError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40001, http_status=400, message="确认用户名不匹配")


class UserHasBusinessRecordsError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40910, http_status=409, message="账号存在业务记录 无法删除 只能停用")


def normalize_username(username: str) -> str:
    """The single normalization rule behind `uq_users_username_normalized`."""
    return username.strip().casefold()


def default_template_fields() -> list[dict[str, Any]]:
    return [
        {
            "field_key": generate_ulid(),
            "label": "今日工作内容",
            "description": "",
            "field_type": "textarea",
            "required": True,
            "enabled": True,
            "sort_order": 10,
            "options": [],
            "core_type": "today_work",
        },
        {
            "field_key": generate_ulid(),
            "label": "明日工作计划",
            "description": "",
            "field_type": "textarea",
            "required": True,
            "enabled": True,
            "sort_order": 20,
            "options": [],
            "core_type": "tomorrow_plan",
        },
    ]


async def create_default_user_resources(session: AsyncSession, *, user_id: str) -> None:
    settings_repository = UserSettingsRepository(session)
    template_repository = TemplateRepository(session)
    await settings_repository.add(UserSettings(user_id=user_id))

    template = ReportTemplate(
        id=generate_ulid(),
        user_id=user_id,
        name=DEFAULT_TEMPLATE_NAME,
        current_version_no=1,
    )
    await template_repository.add_template(template)
    await template_repository.add_version(
        TemplateVersion(
            id=generate_ulid(),
            template_id=template.id,
            version_no=1,
            fields_json=json.dumps(default_template_fields(), ensure_ascii=False),
            created_by=user_id,
        )
    )


class UserService:
    def __init__(self, session: AsyncSession, *, clock: Clock = utc_now) -> None:
        self._session = session
        self._clock = clock
        self._users = UserRepository(session)
        self._audit = AdminAuditRepository(session)

    async def list_users(self, *, page: int, page_size: int) -> tuple[list[User], int]:
        return await self._users.list_page(page=page, page_size=page_size)

    async def get_user(self, user_id: str) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        return user

    async def deletion_eligibility(
        self, users: list[User], *, actor_id: str
    ) -> dict[str, str | None]:
        """Non-sensitive `cannot_delete_reason` per user (`docs/方案设计.md` §7.3).

        A UI hint only: `delete_user()` re-checks every condition itself, so
        a stale eligibility read here can never let an actual deletion
        bypass a guard.
        """
        candidate_ids = [user.id for user in users if user.id != actor_id]
        business_ids = await self._users.has_business_records_bulk(candidate_ids)
        active_admin_count = await self._users.count_active_admins()
        reasons: dict[str, str | None] = {}
        for user in users:
            if user.id == actor_id:
                reasons[user.id] = "self"
            elif user.role == "admin" and user.is_active and active_admin_count <= 1:
                reasons[user.id] = "last_active_admin"
            elif user.id in business_ids:
                reasons[user.id] = "has_business_records"
            else:
                reasons[user.id] = None
        return reasons

    async def create_user(
        self, *, username: str, password: str, display_name: str, role: str
    ) -> User:
        now = self._clock()
        user = User(
            id=generate_ulid(),
            username=username.strip(),
            username_normalized=normalize_username(username),
            display_name=display_name.strip(),
            password_hash=hash_password(password),
            role=role,
            password_changed_at=now,
        )
        try:
            await self._users.add(user)
            await create_default_user_resources(self._session, user_id=user.id)
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            raise UsernameAlreadyExistsError() from error
        return user

    async def update_user(
        self,
        user_id: str,
        *,
        display_name: str | None,
        role: str | None,
        is_active: bool | None,
    ) -> User:
        await self.get_user(user_id)
        updated = await self._users.update_account(
            user_id,
            display_name=display_name.strip() if display_name is not None else None,
            role=role,
            is_active=is_active,
            updated_at=self._clock(),
        )
        if not updated:
            if await self._users.get_by_id(user_id) is None:
                raise UserNotFoundError()
            raise LastActiveAdminError()
        await self._session.commit()
        return await self.get_user(user_id)

    async def reset_password(self, user_id: str, *, new_password: str) -> User:
        changed_at = self._clock()
        updated = await self._users.update_password(
            user_id,
            password_hash=hash_password(new_password),
            password_changed_at=changed_at,
            must_change_password=True,
        )
        if not updated:
            raise UserNotFoundError()
        await self._session.commit()
        return await self.get_user(user_id)

    async def delete_user(
        self,
        actor: User,
        user_id: str,
        *,
        confirm_username: str,
        reason: str,
    ) -> None:
        if user_id == actor.id:
            raise CannotDeleteSelfError()
        target = await self.get_user(user_id)
        if target.username != confirm_username:
            raise UsernameConfirmationMismatchError()
        if await self._users.has_business_records(user_id):
            raise UserHasBusinessRecordsError()

        now = self._clock()
        try:
            deleted = await self._users.delete_if_no_business_records(user_id)
        except IntegrityError as error:
            # A business record was created concurrently between the check
            # above and this DELETE; `ON DELETE RESTRICT` is the final
            # backstop `database.md` §8.4 requires for that race.
            await self._session.rollback()
            raise UserHasBusinessRecordsError() from error
        if not deleted:
            await self._session.rollback()
            if await self._users.get_by_id(user_id) is None:
                raise UserNotFoundError()
            raise LastActiveAdminError()

        await self._audit.add(
            AdminAuditEvent(
                id=generate_ulid(),
                action=_USER_DELETED_ACTION,
                actor_user_id=actor.id,
                actor_username_snapshot=actor.username,
                target_type="user",
                target_id=target.id,
                target_owner_id=target.id,
                reason=reason,
                metadata_json=json.dumps(
                    {"deleted_username": target.username, "deleted_role": target.role},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                created_at=now,
            )
        )
        await self._session.commit()
