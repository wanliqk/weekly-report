import json

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, utc_now
from app.core.errors import AppError
from app.core.ulid import generate_ulid
from app.models import ReportTemplate, TemplateVersion
from app.repositories.template import TemplateRepository
from app.schemas.template import TemplateFieldData, TemplateFieldInput

_FIELDS_ADAPTER = TypeAdapter(list[TemplateFieldData])
_SELECT_TYPES = {"select", "multiselect"}


class TemplateNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40401, http_status=404, message="日报模板不存在")


class TemplateRuleError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(code=40001, http_status=400, message=message)


class TemplateVersionConflictError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40904, http_status=409, message="模板已被更新。请重新加载。")


def parse_template_fields(fields_json: str) -> list[TemplateFieldData]:
    try:
        return _FIELDS_ADAPTER.validate_json(fields_json)
    except ValidationError as error:
        raise RuntimeError("stored template fields are invalid") from error


def _normalized_options(field: TemplateFieldInput) -> list[str]:
    options = [option.strip() for option in field.options]
    if any(not option for option in options):
        raise TemplateRuleError(f"字段“{field.label}”的选项不能为空")
    if len({option.casefold() for option in options}) != len(options):
        raise TemplateRuleError(f"字段“{field.label}”的选项不能重复")
    if field.field_type in _SELECT_TYPES and not options:
        raise TemplateRuleError(f"字段“{field.label}”必须至少配置一个选项")
    if field.field_type not in _SELECT_TYPES and options:
        raise TemplateRuleError(f"字段“{field.label}”的类型不支持选项")
    return options


def build_next_template_fields(
    inputs: list[TemplateFieldInput], current_fields: list[TemplateFieldData]
) -> list[TemplateFieldData]:
    current_by_key = {field.field_key: field for field in current_fields}
    required_core_keys = {
        field.field_key for field in current_fields if field.core_type is not None
    }
    next_fields: list[TemplateFieldData] = []
    seen_keys: set[str] = set()
    seen_orders: set[int] = set()

    for field in inputs:
        key = field.field_key or generate_ulid()
        existing = current_by_key.get(key)
        if field.field_key is not None and existing is None:
            raise TemplateRuleError("字段标识无效。请重新加载模板。")
        if key in seen_keys:
            raise TemplateRuleError("字段标识不能重复")
        if field.sort_order in seen_orders:
            raise TemplateRuleError("字段排序值不能重复")
        seen_keys.add(key)
        seen_orders.add(field.sort_order)
        next_fields.append(
            TemplateFieldData(
                field_key=key,
                label=field.label,
                description=field.description,
                field_type=field.field_type,
                required=field.required,
                enabled=field.enabled,
                show_in_export=field.show_in_export,
                sort_order=field.sort_order,
                options=_normalized_options(field),
                core_type=existing.core_type if existing is not None else None,
            )
        )

    if not required_core_keys.issubset(seen_keys):
        raise TemplateRuleError("核心字段不能删除")
    if not any(field.core_type is not None and field.enabled for field in next_fields):
        raise TemplateRuleError("至少启用一个核心字段")
    return sorted(next_fields, key=lambda field: field.sort_order)


class TemplateService:
    def __init__(self, session: AsyncSession, *, clock: Clock = utc_now) -> None:
        self._session = session
        self._clock = clock
        self._templates = TemplateRepository(session)

    async def get_current(
        self, owner_id: str
    ) -> tuple[ReportTemplate, TemplateVersion, list[TemplateFieldData]]:
        template = await self._templates.get_for_owner(owner_id)
        if template is None:
            raise TemplateNotFoundError()
        version = await self._templates.get_version(template.id, template.current_version_no)
        if version is None:
            raise RuntimeError("current template version is missing")
        return template, version, parse_template_fields(version.fields_json)

    async def list_versions(self, owner_id: str) -> list[TemplateVersion]:
        template = await self._templates.get_for_owner(owner_id)
        if template is None:
            raise TemplateNotFoundError()
        return await self._templates.list_versions(template.id)

    async def publish(
        self, owner_id: str, *, fields: list[TemplateFieldInput]
    ) -> tuple[ReportTemplate, TemplateVersion, list[TemplateFieldData]]:
        template, _current_version, current_fields = await self.get_current(owner_id)
        next_fields = build_next_template_fields(fields, current_fields)
        next_version_no = template.current_version_no + 1
        version = TemplateVersion(
            id=generate_ulid(),
            template_id=template.id,
            version_no=next_version_no,
            fields_json=json.dumps(
                [field.model_dump(mode="json") for field in next_fields],
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            created_by=owner_id,
        )
        try:
            await self._templates.add_version(version)
            advanced = await self._templates.advance_current_version(
                template_id=template.id,
                owner_id=owner_id,
                expected_version_no=template.current_version_no,
                next_version_no=next_version_no,
                updated_at=self._clock(),
            )
            if not advanced:
                await self._session.rollback()
                raise TemplateVersionConflictError()
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            raise TemplateVersionConflictError() from error
        return template, version, next_fields
