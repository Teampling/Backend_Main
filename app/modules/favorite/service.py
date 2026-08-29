from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.modules.favorite.models import Favorite
from app.modules.favorite.repository import FavoriteRepository
from app.modules.project.service import ProjectService


class FavoriteService:
    def __init__(
        self,
        session: AsyncSession,
        repository: FavoriteRepository,
        project_service: ProjectService,
    ):
        self.session = session
        self.repository = repository
        self.project_service = project_service

    async def create(self, project_id: UUID, member_id: UUID) -> Favorite:
        project = await self.project_service.get(project_id, include_deleted=False)
        if not project:
            raise AppError.not_found(f"Project[{project_id}]")

        exists = await self.repository.get_by_project_member(project_id, member_id)
        if exists:
            raise AppError.bad_request("이미 즐겨찾기한 프로젝트입니다.")

        favorite = Favorite(
            project_id=project_id,
            member_id=member_id,
        )

        try:
            created = await self.repository.create_favorite(favorite)
            await self.session.commit()
            await self.session.refresh(created)
            return created

        except IntegrityError:
            await self.session.rollback()
            raise AppError.bad_request("즐겨찾기 추가 중 무결성 오류가 발생했습니다.")

    async def delete(self, project_id: UUID, member_id: UUID) -> None:
        favorite = await self.repository.get_by_project_member(project_id, member_id)
        if not favorite:
            raise AppError.not_found("즐겨찾기하지 않은 프로젝트입니다.")

        try:
            await self.repository.delete_favorite(favorite)
            await self.session.commit()

        except Exception:
            await self.session.rollback()
            raise

    async def favorite(self, project_id: UUID, member_id: UUID) -> bool:
        favorite = await self.repository.get_by_project_member(project_id, member_id)

        if favorite:
            await self.delete(project_id, member_id)
            return False

        await self.create(project_id, member_id)
        return True