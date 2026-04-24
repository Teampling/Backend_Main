from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.modules.work.models import Work
from app.shared.enums import WorkState


class WorkRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, work_id: UUID, *, include_deleted: bool = False) -> Work | None:
        query = select(Work).where(Work.id == work_id)
        if not include_deleted:
            query = query.where(Work.is_deleted == False)
        return await self.session.scalar(query)

    async def list(
            self,
            *,
            keyword: str | None = None,
            author_id: UUID | None = None,
            project_id: UUID | None = None,
            states: list[WorkState] | None = None,
            offset: int = 0,
            limit: int = 100,
            include_deleted: bool = False,
    ) -> list[Work]:
        stmt = select(Work)

        if keyword:
            stmt = stmt.where(
                or_(
                    Work.title.ilike(f"%{keyword}%"),
                    Work.detail.ilike(f"%{keyword}%")
                )
            )

        if author_id:
            stmt = stmt.where(Work.author_id == author_id)

        if project_id:
            stmt = stmt.where(Work.project_id == project_id)

        if states:
            stmt = stmt.where(Work.state.in_(states))

        if not include_deleted:
            stmt = stmt.where(Work.is_deleted == False)

        stmt = stmt.order_by(Work.created_at.desc()).offset(offset).limit(limit)
        return (await self.session.scalars(stmt)).all()

    async def count(
            self,
            *,
            keyword: str | None = None,
            author_id: UUID | None = None,
            project_id: UUID | None = None,
            states: "list[WorkState] | None" = None,
            include_deleted: bool = False) -> int:
        stmt = select(func.count()).select_from(Work)

        if keyword:
            stmt = stmt.where(
                or_(
                    Work.title.ilike(f"%{keyword}%"),
                    Work.detail.ilike(f"%{keyword}%")
                )
            )

        if author_id:
            stmt = stmt.where(Work.author_id == author_id)

        if project_id:
            stmt = stmt.where(Work.project_id == project_id)

        if states:
            stmt = stmt.where(Work.state.in_(states))

        if not include_deleted:
            stmt = stmt.where(Work.is_deleted == False)

        return int(await self.session.scalar(stmt) or 0)

    async def get_stats_by_project(self, project_id: UUID) -> dict[str, int]:
        stmt = (
            select(Work.state, func.count(Work.id))
            .where(Work.project_id == project_id)
            .where(Work.is_deleted == False)
            .group_by(Work.state)
        )
        results = await self.session.execute(stmt)
        stats = {state.value: count for state, count in results.all()}
        
        # 모든 상태에 대해 기본값 0 설정
        for state in WorkState:
            if state.value not in stats:
                stats[state.value] = 0
                
        return stats

    async def save(self, work: Work) -> Work:
        self.session.add(work)
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