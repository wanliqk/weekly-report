from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExportJob


class ExportJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, job: ExportJob) -> None:
        self._session.add(job)
        await self._session.flush()

    async def get_for_owner(self, job_id: str, owner_id: str) -> ExportJob | None:
        result = await self._session.execute(
            select(ExportJob).where(ExportJob.id == job_id, ExportJob.user_id == owner_id)
        )
        return result.scalar_one_or_none()

    async def list_expired_with_files(self, *, now: datetime) -> list[ExportJob]:
        """Succeeded jobs past `expires_at` that still reference a temp file.

        Used only by the startup cleanup sweep (`ExportService.cleanup_expired`),
        not by any owner-scoped business read, so it intentionally has no
        `user_id` filter — it walks every user's stale export files.
        """
        result = await self._session.execute(
            select(ExportJob).where(
                ExportJob.status == "succeeded",
                ExportJob.expires_at <= now,
                ExportJob.file_path.is_not(None),
            )
        )
        return list(result.scalars())
