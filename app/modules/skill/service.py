import logging
from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.modules.skill.models import Skill
from app.modules.skill.repository import SkillRepository
from app.modules.skill.schemas import SkillCreateIn, SkillUpdateIn
from app.shared.storage.oci_object_storage import OCIObjectStorageClient

logger = logging.getLogger(__name__)

class SkillService:
    def __init__(
            self,
            session: AsyncSession,
            storage: OCIObjectStorageClient,
    ):
        self.session = session
        self.repo = SkillRepository(session)
        self.storage = storage

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

    async def create(
            self,
            data: SkillCreateIn,
            icon_file: UploadFile | None = None,
    ) -> Skill:
        existing = await self.repo.get_by_name(data.name)
        if existing:
            raise AppError.bad_request(f"[{data.name}]은(는) 이미 존재하는 스킬 이름입니다.")

        payload = data.model_dump(mode="json")

        icon_object_name = None
        if icon_file is not None:
            icon_object_name = await self.storage.upload_object(file=icon_file, object_prefix="skill")
            icon_object_url = self.storage.build_object_url(icon_object_name)
            payload["img_url"] = icon_object_url

        skill = Skill(**payload)

        try:
            saved = await self.repo.save(skill)
            await self.session.commit()
            await self.session.refresh(saved)
            return saved
        except IntegrityError as e:
            if icon_object_name:
                try:
                    await self.storage.delete_object(icon_object_name)
                except Exception:
                    logger.error(f"업로드 실패 후 이미지 롤백 삭제 실패: {icon_object_name}",exc_info=True)
            await self.session.rollback()
            raise AppError.bad_request(f"스킬 생성 중 DB 무결성 오류가 발생했습니다: {str(e)}")

    async def update(
            self,
            skill_id: UUID,
            data: SkillUpdateIn,
            icon_file: UploadFile | None = None,
    ) -> Skill:
        skill = await self.repo.get_by_id(skill_id, include_deleted=False)
        if not skill:
            raise AppError.not_found(f"Skill[{skill_id}]")

        patch = data.model_dump(mode="json", exclude_unset=True)

        if "name" in patch:
            new_name = patch["name"]
            existing = await self.repo.get_by_name(new_name)
            if existing and existing.id != skill.id:
                raise AppError.bad_request(f"[{new_name}]은(는) 이미 존재하는 스킬 이름입니다.")

        old_image_url = skill.img_url
        icon_object_name = None

        if icon_file is not None:
            icon_object_name = await self.storage.upload_object(file=icon_file, object_prefix="skill")
            icon_object_url = self.storage.build_object_url(icon_object_name)
            patch["img_url"] = icon_object_url
        else:
            patch["img_url"] = None

        for k, v in patch.items():
            setattr(skill, k, v)

        try:
            updated = await self.repo.save(skill)
            await self.session.commit()
            await self.session.refresh(updated)

            if old_image_url:
                try:
                    old_object_name = self.storage.extract_object_name(old_image_url)
                    await self.storage.delete_object(old_object_name)
                except Exception:
                    logger.error(f"기존 이미지 삭제 실패: {old_image_url}",exc_info=True)

            return updated

        except IntegrityError as e:
            if icon_object_name:
                try:
                    await self.storage.delete_object(icon_object_name)
                except Exception:
                    logger.error(f"업로드 실패 후 이미지 롤백 삭제 실패: {icon_object_name}",exc_info=True)
            await self.session.rollback()
            raise AppError.bad_request(f"스킬 생성 중 DB 무결성 오류가 발생했습니다: {str(e)}")

    async def delete(self, skill_id: UUID, *, hard: bool = False) -> None:
        skill = await self.get(skill_id, include_deleted=True)

        image_url = skill.img_url

        try:
            if hard:
                await self.repo.hard_delete(skill)
                await self.session.commit()
                if image_url:
                    try:
                        old_object_name = self.storage.extract_object_name(image_url)
                        await self.storage.delete_object(old_object_name)
                    except Exception:
                        logger.error(f"기존 이미지 삭제 실패: {image_url}", exc_info=True)
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