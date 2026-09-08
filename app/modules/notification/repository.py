from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notification.models import OutboxEvent
from app.shared.enums import NotificationEventType


class OutboxEventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def enqueue(
            self,
            *,
            event_type: NotificationEventType,
            title: str,
            detail: str | None,
            target_type: int,
            target_id: UUID | None,
            recipient_ids: list[UUID],
    ) -> OutboxEvent:
        event = OutboxEvent(
            event_type=event_type,
            payload={
                "event_type": event_type.value,
                "title": title,
                "detail": detail,
                "target_type": int(target_type),
                "target_id": str(target_id) if target_id else None,
                "recipient_ids": [str(member_id) for member_id in dict.fromkeys(recipient_ids)],
            },
        )
        self.session.add(event)
        return event