from typing import Annotated

from fastapi import Depends

from app.core.database import DbSessionDep
from app.modules.notice.repository import NoticeRepository
from app.modules.notice.service import NoticeService


def get_notice_service(session: DbSessionDep) -> NoticeService:
    repository = NoticeRepository(session)
    return NoticeService(session, repository)


NoticeServiceDep = Annotated[NoticeService, Depends(get_notice_service)]
