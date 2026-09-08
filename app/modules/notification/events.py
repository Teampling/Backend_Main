from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notification.repository import OutboxEventRepository
from app.shared.enums import NotificationEventType, NotificationTargetType


class NotificationEvents:

    @staticmethod
    def notice_created(
            session: AsyncSession,
            *,
            notice_id: UUID,
            title: str,
            detail: str | None,
            recipient_ids: list[UUID],
    ) -> None:
        if not recipient_ids:
            return

        OutboxEventRepository(session).enqueue(
            event_type=NotificationEventType.NOTICE_CREATED,
            title=title,
            detail=detail,
            target_type=NotificationTargetType.NOTICE,
            target_id=notice_id,
            recipient_ids=recipient_ids,
        )