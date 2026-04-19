from typing import Annotated

from fastapi import Depends

from app.core.database import DbSessionDep
from app.modules.project.repository import ProjectRepository
from app.modules.project.service import ProjectService


def get_project_service(session: DbSessionDep) -> ProjectService:
    repository = ProjectRepository(session)
    return ProjectService(session, repository)

ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]