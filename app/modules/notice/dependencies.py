from typing import Annotated

from fastapi import Depends

from app.core.database import DbSessionDep
from app.modules.notice.repository import NoticeRepository
from app.modules.notice.service import NoticeService
from app.modules.project.repository import ProjectRepository


def get_notice_service(session: DbSessionDep) -> NoticeService:
    repository = NoticeRepository(session)
    project_repository = ProjectRepository(session)
    return NoticeService(session, repository, project_repository)


NoticeServiceDep = Annotated[NoticeService, Depends(get_notice_service)]
