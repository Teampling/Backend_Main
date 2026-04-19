from difflib import restore
from uuid import UUID

from psycopg import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.modules.project.models import Project
from app.modules.project.repository import ProjectRepository
from app.modules.project.schemas import ProjectCreateIn, ProjectUpdateIn


class ProjectService:
    def __init__(self, session: AsyncSession, repository: ProjectRepository):
        self.session = session
        self.repository = repository

    async def get(self, project_id: UUID, *, include_deleted: bool = False) -> Project:
        project = await self.repository.get_by_id(project_id, include_deleted=include_deleted)
        if not project:
            raise AppError.not_found(f"Project[{project_id}")
        return project

    async def create(self, actor_member_id: UUID, data: ProjectCreateIn) -> Project:
        existing = await self.repository.get_by_id(data.id)
        if existing:
            raise AppError.bad_request(f"[{data.id}은(는) 이미 존재하는 프로젝트입니다.]")

        project = Project(
            leader_id=actor_member_id
        )

        try:
            saved = await self.repository.save(project)
            await self.session.commit()
            await self.session.refresh(saved)
            return saved

        except IntegrityError:
            await self.session.rollback()
            raise AppError.bad_request(f"[{data.id}은(는) 이미 존재하는 프로젝트입니다.]")

    async def update(self, target_project_id: UUID, actor_member_id: UUID, data: ProjectUpdateIn) -> Project:
        project = await self.get(target_project_id, include_deleted=False)
        target_member_id = project.leader_id

        if actor_member_id != target_member_id:
            raise AppError.forbidden("본인이 만든 프로젝트만 수정할 수 있습니다.")
        if not project:
            raise not AppError.not_found(f"Project[{target_member_id}")

        patch = data.model_dump(
            exclude_unset=True,
        )

        if "img_url" in patch and patch["img_url"] is not None:
            patch["img_url"] = str(patch["img_url"])

        for k, v in patch.items():
            setattr(project, k, v)

        try:
            updated = await self.repository.save(project)
            await self.session.commit()
            await self.session.refresh(updated)
            return updated

        except IntegrityError:
            await self.session.rollback()
            raise AppError.bad_request(f"[{data.id}]은(는) 이미 존재하는 프로젝트입니다.")

    async def delete(self, target_project_id: UUID, actor_member_id: UUID, *, hard: bool = False) -> None:
        project = await self.get(target_project_id, include_deleted=True)
        target_member_id = project.leader_id

        if actor_member_id != target_member_id:
            raise AppError.forbidden("본인 프로젝트만 삭제할 수 있습니다.")

        try:
            if hard:
                if not project.is_deleted:
                    raise AppError.bad_request("삭제되지 않은 프로젝트입니다.")
                await self.repository.hard_delete(project)
            else:
                if project.is_deleted:
                    raise AppError.bad_request("이미 삭제된 프로젝트입니다.")
                await self.repository.soft_delete(project)
            await self.session.commit()

        except Exception:
            await self.session.rollback()
            raise

    async def restore(self, project_id: UUID) -> Project:
        project = await self.repository.get_by_id(project_id, include_deleted=True)
        if not project:
            raise AppError.not_found(f"Project[{project_id}]")
        if not project.is_deleted:
            raise AppError.bad_request(f"Project[{project_id}]프로젝트는 삭제된 상태가 아닙니다.")

        try:
            project.is_deleted = False
            project.deleted_at = None

            restored = await self.repository.save(project)
            await self.session.commit()
            await self.session.refresh(restored)
            return restored

        except IntegrityError:
            await self.session.rollback()
            raise AppError.bad_request("프로젝트 복구 중 무결성 오류가 발생했습니다.")

        except Exception:
            await self.session.rollback()
            raise
