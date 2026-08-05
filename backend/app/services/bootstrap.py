import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, utc_now
from app.core.errors import AppError
from app.core.security import hash_password
from app.core.ulid import generate_ulid
from app.models import ReportTemplate, TemplateVersion, User, UserSettings
from app.repositories.template import TemplateRepository
from app.repositories.user import UserRepository
from app.repositories.user_settings import UserSettingsRepository
from app.services.user import normalize_username

ALREADY_INITIALIZED_CODE = 40001
DEFAULT_TEMPLATE_NAME = "日报模板"


class AlreadyInitializedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code=ALREADY_INITIALIZED_CODE,
            http_status=400,
            message="系统已完成初始化 无法重复创建管理员",
        )


def _default_template_fields() -> list[dict[str, Any]]:
    """Core fields per requirements.md 4.2: not deletable, at least one enabled."""
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


class BootstrapService:
    """First-admin init: user + settings + template + version in one transaction."""

    def __init__(self, session: AsyncSession, *, clock: Clock = utc_now) -> None:
        self._session = session
        self._clock = clock
        self._users = UserRepository(session)
        self._user_settings = UserSettingsRepository(session)
        self._templates = TemplateRepository(session)

    async def is_initialized(self) -> bool:
        return await self._users.any_exists()

    async def bootstrap_admin(self, *, username: str, password: str, display_name: str) -> User:
        user = User(
            id=generate_ulid(),
            username=username,
            username_normalized=normalize_username(username),
            display_name=display_name,
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
        refreshed_user = await self._session.get(User, user.id)
        assert refreshed_user is not None
        user = refreshed_user

        await self._user_settings.add(UserSettings(user_id=user.id))

        template = ReportTemplate(
            id=generate_ulid(),
            user_id=user.id,
            name=DEFAULT_TEMPLATE_NAME,
            current_version_no=1,
        )
        await self._templates.add_template(template)

        version = TemplateVersion(
            id=generate_ulid(),
            template_id=template.id,
            version_no=1,
            fields_json=json.dumps(_default_template_fields(), ensure_ascii=False),
            created_by=user.id,
        )
        await self._templates.add_version(version)

        await self._session.commit()
        return user
