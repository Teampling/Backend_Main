from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.modules.notice.models import Notice


class NoticeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, notice_id: UUID, *, include_deleted: bool = False) -> Notice | None:
        query = select(Notice).where(Notice.id == notice_id)
        if not include_deleted:
            query = query.where(Notice.is_deleted == False)
        return await self.session.scalar(query)

    async def list(
            self,
            *,
            keyword: str | None = None,
            project_id: UUID | None = None,
            offset: int = 0,
            limit: int = 100,
            include_deleted: bool = False,
    ) -> list[Notice]:
        stmt = select(Notice)

        if keyword:
            stmt = stmt.where(
                or_(
                    Notice.title.ilike(f"%{keyword}%"),
                    Notice.detail.ilike(f"%{keyword}%")
                )
            )

        if project_id:
            stmt = stmt.where(Notice.project_id == project_id)

        if not include_deleted:
            stmt = stmt.where(Notice.is_deleted == False)

        stmt = stmt.order_by(Notice.created_at.desc()).offset(offset).limit(limit)
        return (await self.session.scalars(stmt)).all()

    async def count(
            self,
            *,
            keyword: str | None = None,
            project_id: UUID | None = None,
            include_deleted: bool = False
    ) -> int:
        stmt = select(func.count()).select_from(Notice)

        if keyword:
            stmt = stmt.where(
                or_(
                    Notice.title.ilike(f"%{keyword}%"),
                    Notice.detail.ilike(f"%{keyword}%")
                )
            )

        if project_id:
            stmt = stmt.where(Notice.project_id == project_id)

        if not include_deleted:
            stmt = stmt.where(Notice.is_deleted == False)

        return int(await self.session.scalar(stmt) or 0)

    async def save(self, notice: Notice) -> Notice:
        self.session.add(notice)
        await self.session.flush()
        await self.session.refresh(notice)
        return notice

    async def soft_delete(self, notice: Notice) -> Notice:
        notice.is_deleted = True
        notice.deleted_at = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(notice)
        return notice

    async def hard_delete(self, notice: Notice) -> None:
        await self.session.delete(notice)
        await self.session.flush()
