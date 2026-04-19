from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.modules.project.models import Project
from app.modules.project.models import ProjectMember


class ProjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, project_id: UUID, *, include_deleted: bool = False) -> Project | None:
        query = select(Project).where(Project.id == project_id)
        if not include_deleted:
            query = query.where(Project.is_deleted == False)
        return await self.session.scalar(query)

    async def list(
            self,
            *,
            keyword: str | None = None,
            start_after: datetime | None = None,
            end_before: datetime | None = None,
            offset: int = 0,
            limit: int = 100,
            include_deleted: bool = False,
    ) -> list[Project]:
        stmt = select(Project)

        if keyword:
            stmt = stmt.where(
                (Project.name.ilike(f"%{keyword}%")) |
                (Project.detail.ilike(f"%{keyword}%"))
            )

        if start_after:
            stmt = stmt.where(Project.start_date >= start_after)

        if end_before:
            stmt = stmt.where(Project.end_date <= end_before)

        if not include_deleted:
            stmt = stmt.where(Project.is_deleted == False)

        stmt = stmt.order_by(Project.created_at.desc()).offset(offset).limit(limit)
        return (await self.session.scalars(stmt)).all()

    async def count(
            self,
            *,
            keyword: str | None = None,
            start_after: datetime | None = None,
            end_before: datetime | None = None,
            include_deleted: bool = False) -> int:
        stmt = select(func.count()).select_from(Project)

        if keyword:
            stmt = stmt.where(
                (Project.name.ilike(f"%{keyword}%")) |
                (Project.detail.ilike(f"%{keyword}%"))
            )

        if start_after:
            stmt = stmt.where(Project.start_date >= start_after)

        if end_before:
            stmt = stmt.where(Project.end_date <= end_before)

        if not include_deleted:
            stmt = stmt.where(Project.is_deleted == False)

        return int(await self.session.scalar(stmt) or 0)

    async def save(self, project: Project) -> Project:
        self.session.add(project)
        await self.session.flush()
        return project

    async def get_member_count(self, project_id: UUID) -> int:

        stmt = select(func.count()).select_from(ProjectMember).where(ProjectMember.project_id == project_id)
        return int(await self.session.scalar(stmt) or 0)

    async def soft_delete(self, project: Project) -> Project:
        project.is_deleted = True
        project.deleted_at = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def hard_delete(self, project: Project) -> None:
        await self.session.delete(project)
        await self.session.flush()