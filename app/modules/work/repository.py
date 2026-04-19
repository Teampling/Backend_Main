from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.modules.work.models import Work


class WorkRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, work_id: UUID, *, include_deleted: bool = False) -> Work | None:
        query = select(Work).where(Work.id == work_id)
        if not include_deleted:
            query = query.where(Work.is_deleted == False)
        return await self. session.scalar(query)

    async def list(
            self,
            *,
            keyword: str | None = None,
            offset: int = 0,
            limit: int = 100,
            include_deleted: bool = False,
    ) -> list[Work]:
        stmt = select(Work)

        if keyword:
            stmt = stmt.where(Work.name.ilike(f"%{keyword}%"))

        if not include_deleted:
            stmt = stmt.where(Work.is_deleted == False)

        stmt = stmt.order_by(Work.name.asc()).offset(offset).limit(limit)
        return (await self.session.scalars(stmt)).all()

    async def count(
            self,
            *,
            keyword: str | None = None,
            include_deleted: bool = False) -> int:
        stmt = select(func.count()).select_from(Work)

        if keyword:
            stmt = stmt.where(Work.name.ilike(f"%{keyword}%"))

        if not include_deleted:
            stmt = stmt.where(Work.is_deleted == False)

        return int(await self.session.scalar(stmt) or 0)

    async def save(self, work: Work) -> Work:
        self.session.add(Work)
        await self.session.flush()
        await self.session.refresh(work)
        return work

    async def soft_delete(self, work: Work) -> Work:
        work.is_deleted = True
        work.deleted_at = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(work)
        return work

    async def hard_delete(self, work: Work) -> None:
        await self.session.delete(work)
        await self.session.flush()