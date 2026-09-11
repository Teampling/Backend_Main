from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.modules.notification.models import OutboxEvent, Notification, NotificationRecipient
from app.shared.enums import NotificationEventType, NotificationTargetType


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
            self,
            *,
            event_type: NotificationEventType,
            title: str,
            detail: str | None,
            target_type: NotificationTargetType,
            target_id: UUID | None,
            project_id: UUID | None,
            recipient_ids: list[UUID],
    ) -> Notification:
        notification = Notification(
            event_type=event_type,
            title=title,
            detail=detail,
            target_type=int(target_type.value),
            target_id=target_id,
            project_id=project_id,
        )
        self.session.add(notification)
        await self.session.flush()
        await self.session.refresh(notification)

        for member_id in dict.fromkeys(recipient_ids):
            self.session.add(NotificationRecipient(notification_id=notification.id, member_id=member_id))

        return notification

    async def list_by_member(
            self,
            member_id: UUID,
            *,
            offset: int = 0,
            limit: int = 100,
            unread_only: bool = False,
    ) -> list[NotificationRecipient]:
        stmt = (
            select(NotificationRecipient)
            .where(
                NotificationRecipient.member_id == member_id,
                NotificationRecipient.is_deleted == False,
            )
            .options(selectinload(NotificationRecipient.notification))
            .order_by(NotificationRecipient.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        if unread_only:
            stmt = stmt.where(NotificationRecipient.read_at.is_(None))

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_member(
            self,
            member_id: UUID,
            *,
            unread_only: bool = False,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(NotificationRecipient)
            .where(
                NotificationRecipient.member_id == member_id,
                NotificationRecipient.is_deleted == False,
            )
        )

        if unread_only:
            stmt = stmt.where(NotificationRecipient.read_at.is_(None))

        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_recipient(
            self,
            member_id: UUID,
            notification_id: UUID,
    ) -> NotificationRecipient | None:
        stmt = select(NotificationRecipient).where(
            NotificationRecipient.member_id == member_id,
            NotificationRecipient.notification_id == notification_id,
            NotificationRecipient.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_all_read(self, member_id: UUID) -> int:
        stmt = (
            update(NotificationRecipient)
            .where(
                NotificationRecipient.member_id == member_id,
                NotificationRecipient.read_at.is_(None),
                NotificationRecipient.is_deleted == False,
            )
            .values(read_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(stmt)
        return result.rowcount

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
            project_id: UUID | None,
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
                "project_id": str(project_id) if project_id else None,
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