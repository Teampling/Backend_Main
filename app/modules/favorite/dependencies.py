from typing import Annotated

from fastapi import Depends

from app.core.database import DbSessionDep
from app.modules.favorite.repository import FavoriteRepository
from app.modules.favorite.service import FavoriteService
from app.modules.project.dependencies import get_project_service


def get_favorite_service(session: DbSessionDep) -> FavoriteService:
    repository = FavoriteRepository(session)
    project_service = get_project_service(session)
    return FavoriteService(session, repository, project_service)


FavoriteServiceDep = Annotated[FavoriteService, Depends(get_favorite_service)]