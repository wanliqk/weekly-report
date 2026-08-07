from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminAuditEvent


class AdminAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: AdminAuditEvent) -> None:
        self._session.add(event)
        await self._session.flush()

    async def get_latest_for_target(self, *, action: str, target_id: str) -> AdminAuditEvent | None:
        result = await self._session.execute(
            select(AdminAuditEvent)
            .where(AdminAuditEvent.action == action, AdminAuditEvent.target_id == target_id)
            .order_by(AdminAuditEvent.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_page(
        self,
        *,
        action: str | None,
        date_from: date | None,
        date_to: date | None,
        page: int,
        page_size: int,
    ) -> tuple[list[AdminAuditEvent], int]:
        filters = []
        if action is not None:
            filters.append(AdminAuditEvent.action == action)
        if date_from is not None:
            filters.append(func.date(AdminAuditEvent.created_at) >= date_from.isoformat())
        if date_to is not None:
            filters.append(func.date(AdminAuditEvent.created_at) <= date_to.isoformat())
        total_result = await self._session.execute(
            select(func.count()).select_from(AdminAuditEvent).where(*filters)
        )
        items_result = await self._session.execute(
            select(AdminAuditEvent)
            .where(*filters)
            .order_by(AdminAuditEvent.created_at.desc(), AdminAuditEvent.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(items_result.scalars()), total_result.scalar_one()
