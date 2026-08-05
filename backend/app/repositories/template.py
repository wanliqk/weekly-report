from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ReportTemplate, TemplateVersion


class TemplateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_template(self, template: ReportTemplate) -> None:
        self._session.add(template)
        await self._session.flush()

    async def add_version(self, version: TemplateVersion) -> None:
        self._session.add(version)
        await self._session.flush()

    async def get_for_owner(self, owner_id: str) -> ReportTemplate | None:
        result = await self._session.execute(
            select(ReportTemplate).where(ReportTemplate.user_id == owner_id)
        )
        return result.scalar_one_or_none()

    async def get_version(self, template_id: str, version_no: int) -> TemplateVersion | None:
        result = await self._session.execute(
            select(TemplateVersion).where(
                TemplateVersion.template_id == template_id,
                TemplateVersion.version_no == version_no,
            )
        )
        return result.scalar_one_or_none()

    async def list_versions(self, template_id: str) -> list[TemplateVersion]:
        result = await self._session.execute(
            select(TemplateVersion)
            .where(TemplateVersion.template_id == template_id)
            .order_by(TemplateVersion.version_no.desc())
        )
        return list(result.scalars())

    async def advance_current_version(
        self,
        *,
        template_id: str,
        owner_id: str,
        expected_version_no: int,
        next_version_no: int,
        updated_at: datetime,
    ) -> bool:
        result = await self._session.execute(
            update(ReportTemplate)
            .where(
                ReportTemplate.id == template_id,
                ReportTemplate.user_id == owner_id,
                ReportTemplate.current_version_no == expected_version_no,
            )
            .values(current_version_no=next_version_no, updated_at=updated_at)
        )
        return bool(result.rowcount == 1)
