from sqlalchemy.exc import IntegrityError
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.modules.skill.modules import Skill
from app.modules.skill.repository import SkillRepository
from app.modules.skill.schemas import SkillCreateIn, SkillUpdateIn


class SkillService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = SkillRepository(session)

    async def get(self, skill_id: UUID, *, include_deleted: bool = False) -> Skill:
        skill = await self.repo.get_by_id(skill_id, include_deleted=include_deleted)
        if not skill:
            raise AppError.not_found(f"Skill[{skill_id}]")
        return skill

    async def list(
        self,
        *,
        keyword: str | None = None,
        page: int = 1,
        size: int = 50,
        include_deleted: bool = False,
    ) -> dict[str, Any]:
        if page < 1:
            page = 1
        if size < 1:
            size = 1
        if size > 100:
            size = 100

        offset = (page - 1) * size

        items = await self.repo.list(
            keyword=keyword,
            offset=offset,
            limit=size,
            include_deleted=include_deleted,
        )
        total = await self.repo.count(
            keyword=keyword,
            include_deleted=include_deleted,
        )
        return {"items": items, "page": page, "size": size, "total": total}

    async def create(self, data: SkillCreateIn) -> Skill:
        existing = await self.repo.get_by_name(data.name)
        if existing:
            raise AppError.bad_request(f"[{data.name}]은(는) 이미 존재하는 스킬 이름입니다.")

        skill = Skill(**data.model_dump(mode="json"))

        try:
            saved = await self.repo.save(skill)
            await self.session.commit()
            await self.session.refresh(saved)
            return saved
        except IntegrityError:
            await self.session.rollback()
            raise AppError.bad_request(f"[{data.name}]은(는) 이미 존재하는 스킬 이름입니다.")

    async def update(self, skill_id: UUID, data: SkillUpdateIn) -> Skill:
        skill = await self.repo.get_by_id(skill_id, include_deleted=False)
        if not skill:
            raise AppError.not_found(f"Skill[{skill_id}]")

        patch = data.model_dump(mode="json", exclude_unset=True)

        if "name" in patch:
            new_name = patch["name"]
            existing = await self.repo.get_by_name(new_name)
            if existing and existing.id != skill.id:
                raise AppError.bad_request(f"[{new_name}]은(는) 이미 존재하는 스킬 이름입니다.")

        for k, v in patch.items():
            setattr(skill, k, v)

        try:
            updated = await self.repo.save(skill)
            await self.session.commit()
            await self.session.refresh(updated)
            return updated
        except IntegrityError:
            await self.session.rollback()
            raise AppError.bad_request(f"[{data.name}]은(는) 이미 존재하는 스킬 이름입니다.")

    async def delete(self, skill_id: UUID, *, hard: bool = False) -> None:
        skill = await self.get(skill_id, include_deleted=True)

        try:
            if hard:
                await self.repo.hard_delete(skill)
            else:
                await self.repo.soft_delete(skill)

            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def restore(self, skill_id: UUID) -> Skill:
        skill = await self.repo.get_by_id(skill_id, include_deleted=True)
        if not skill:
            raise AppError.not_found(f"Skill[{skill_id}]")

        if not skill.is_deleted:
            raise AppError.bad_request(f"Skill[{skill_id}]은(는) 삭제된 상태가 아닙니다.")

        try:
            skill.is_deleted = False
            skill.deleted_at = None

            restored = await self.repo.save(skill)
            await self.session.commit()
            await self.session.refresh(restored)
            return restored
        except IntegrityError:
            await self.session.rollback()
            raise AppError.bad_request("스킬 복구 중 무결성 오류가 발생했습니다.")
        except Exception:
            await self.session.rollback()
            raise