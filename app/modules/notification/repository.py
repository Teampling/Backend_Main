from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

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

    async def get_undispatched(self, limit: int = 100) -> list[OutboxEvent]:
        stmt = (
            select(OutboxEvent)
            .where(OutboxEvent.dispatched_at.is_(None))
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_dispatched(self, event: OutboxEvent) -> None:
        event.dispatched_at = datetime.now(timezone.utc)
        self.session.add(event)

    async def mark_failed(self, event: OutboxEvent) -> None:
        event.attempts += 1
        self.session.add(event)