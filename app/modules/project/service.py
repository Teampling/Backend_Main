from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
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
            raise AppError.not_found(f"Project[{project_id}]")
        return project

    async def create(self, actor_member_id: UUID, data: ProjectCreateIn) -> Project:
        project = Project(
            **data.model_dump(),
            leader_id=actor_member_id
        )

        try:
            saved = await self.repository.save(project)
            await self.session.commit()
            await self.session.refresh(saved)
            return saved

        except IntegrityError:
            await self.session.rollback()
            raise AppError.bad_request(f"[{project.name}]은(는) 이미 존재하는 프로젝트입니다.")

    async def list(
        self,
        *,
        keyword: str | None = None,
        start_after: datetime | None = None,
        end_before: datetime | None = None,
        page: int = 1,
        size: int = 20,
        include_deleted: bool = False,
    ) -> dict[str, Any]:
        if page < 1:
            page = 1
        if size < 1:
            size = 1
        if size > 100:
            size = 100

        offset = (page - 1) * size

        items = await self.repository.list(
            keyword=keyword,
            start_after=start_after,
            end_before=end_before,
            offset=offset,
            limit=size,
            include_deleted=include_deleted,
        )
        total = await self.repository.count(
            keyword=keyword,
            start_after=start_after,
            end_before=end_before,
            include_deleted=include_deleted,
        )

        return {"items": items, "page": page, "size": size, "total": total}

    async def update(self, target_project_id: UUID, actor_member_id: UUID, data: ProjectUpdateIn) -> Project:
        project = await self.get(target_project_id, include_deleted=False)
        if not project:
            raise AppError.not_found(f"Project[{target_project_id}]")

        if actor_member_id != project.leader_id:
            raise AppError.forbidden("본인이 리더인 프로젝트만 수정할 수 있습니다.")

        patch = data.model_dump(
            exclude_unset=True,
        )

        for k, v in patch.items():
            setattr(project, k, v)

        try:
            updated = await self.repository.save(project)
            await self.session.commit()
            await self.session.refresh(updated)
            return updated

        except IntegrityError:
            await self.session.rollback()
            raise AppError.bad_request(f"[{project.name}] 수정 중 오류가 발생했습니다.")

    async def delete(self, target_project_id: UUID, actor_member_id: UUID, *, hard: bool = False) -> None:
        project = await self.get(target_project_id, include_deleted=True)
        if not project:
            raise AppError.not_found(f"Project[{target_project_id}]")

        if actor_member_id != project.leader_id:
            raise AppError.forbidden("본인이 리더인 프로젝트만 삭제할 수 있습니다.")

        member_count = await self.repository.get_member_count(target_project_id)
        if member_count > 1:
            raise AppError.bad_request("나를 제외한 팀원이 남아있는 프로젝트는 삭제할 수 없습니다. 모든 팀원을 내보낸 후 삭제해주세요.")

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
