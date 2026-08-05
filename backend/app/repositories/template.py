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
