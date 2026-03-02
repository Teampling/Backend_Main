from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.modules.skill.modules import Skill
from app.modules.skill.schemas import SkillCreateIn, SkillUpdateIn


class SkillRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, skill_id: int) -> Skill | None:
        stmt = select(Skill).where(Skill.id == skill_id)
        return await self.session.scalar(stmt)

    async def create(self, data: SkillCreateIn) -> Skill:
        skill = Skill(**data.model_dump())
        self.session.add(skill)

        await self.session.flush()
        await self.session.refresh(skill)
        return skill

    async def update(self, skill: Skill, data: SkillUpdateIn) -> Skill:
        patch = data.model_dump(exclude_unset=True)

        for key, value in patch.items():
            setattr(skill, key, value)

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
