from typing import Annotated

from fastapi import Depends

from app.core.database import DbSessionDep
from app.modules.work.repository import WorkRepository
from app.modules.work.service import WorkService


def get_work_service(session: DbSessionDep) -> WorkService:
    repository = WorkRepository(session)
    return WorkService(session, repository)

WorkServiceDep = Annotated[WorkService, Depends(get_work_service)]