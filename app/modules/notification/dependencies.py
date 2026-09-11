from typing import Annotated

from fastapi import Depends

from app.core.database import DbSessionDep
from app.modules.notification.repository import NotificationRepository
from app.modules.notification.service import NotificationService


def get_notification_service(session: DbSessionDep) -> NotificationService:
    repository = NotificationRepository(session)
    return NotificationService(session, repository)


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]
