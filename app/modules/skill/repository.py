from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.modules.skill.modules import Skill


class SkillRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, skill_id: UUID, *, include_deleted: bool = False) -> Skill | None:
        stmt = select(Skill).where(Skill.id == skill_id)
        if not include_deleted:
            stmt = stmt.where(Skill.is_deleted == False)  # noqa: E712
        return await self.session.scalar(stmt)

    async def get_by_name(self, name: str, *, include_deleted: bool = False) -> Skill | None:
        stmt = select(Skill).where(Skill.name == name)
        if not include_deleted:
            stmt = stmt.where(Skill.is_deleted == False)  # noqa: E712
        return await self.session.scalar(stmt)

    async def list(
            self,
            *,
            keyword: str | None = None,
            offset: int = 0,
            limit: int = 50,
            include_deleted: bool = False,
    ) -> list[Skill]:
        stmt = select(Skill)

        if keyword:
            stmt = stmt.where(Skill.name.ilike(f"%{keyword}%"))

        if not include_deleted:
            stmt = stmt.where(Skill.is_deleted == False)

        stmt = stmt.order_by(Skill.name.asc()).offset(offset).limit(limit)
        return (await self.session.scalars(stmt)).all()

    async def count(self, *, keyword: str | None = None, include_deleted: bool = False) -> int:
        stmt = select(func.count()).select_from(Skill)

        if keyword:
            stmt = stmt.where(Skill.name.ilike(f"%{keyword}%"))

        if not include_deleted:
            stmt = stmt.where(Skill.is_deleted == False)

        return int(await self.session.scalar(stmt) or 0)

    async def save(self, skill: Skill) -> Skill:
        self.session.add(skill)
        await self.session.flush()
        await self.session.refresh(skill)
        return skill

    async def soft_delete(self, skill: Skill) -> Skill:
        skill.is_deleted = True
        skill.deleted_at = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(skill)
        return skill

    async def hard_delete(self, skill: Skill) -> None:
        await self.session.delete(skill)
        await self.session.flush()
