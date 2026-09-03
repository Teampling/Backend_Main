from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.notification.models import Notification, NotificationRecipient, OutboxEvent


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_with_recipients(
        self,
        *,
        event_type: str,
        title: str,
        detail: str | None,
        target_type: int,
        target_id: UUID | None,
        recipient_ids: list[UUID],
    ) -> Notification:
        """알림 1건을 만들고, 중복을 제거한 수신자 각각에게 수신함 행을 하나씩 만든다."""
        notification = Notification(
            event_type=event_type,
            title=title,
            detail=detail,
            target_type=int(target_type),
            target_id=target_id,
        )
        self.session.add(notification)
        await self.session.flush()  # notification.id 확보

        for member_id in dict.fromkeys(recipient_ids):
            self.session.add(NotificationRecipient(notification_id=notification.id, member_id=member_id))

        await self.session.commit()
        await self.session.refresh(notification)
        return notification

    async def list_for_member(
        self,
        member_id: UUID,
        *,
        page: int = 1,
        size: int = 20,
        unread_only: bool = False,
    ) -> list[NotificationRecipient]:
        offset = (page - 1) * size
        stmt = (
            select(NotificationRecipient)
            .where(NotificationRecipient.member_id == member_id)
            .options(selectinload(NotificationRecipient.notification))
            .order_by(NotificationRecipient.created_at.desc())
            .offset(offset)
            .limit(size)
        )
        if unread_only:
            stmt = stmt.where(NotificationRecipient.is_read.is_(False))

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_for_member(self, member_id: UUID, *, unread_only: bool = False) -> int:
        stmt = (
            select(func.count())
            .select_from(NotificationRecipient)
            .where(NotificationRecipient.member_id == member_id)
        )
        if unread_only:
            stmt = stmt.where(NotificationRecipient.is_read.is_(False))

        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_recipient(self, recipient_id: UUID, member_id: UUID) -> NotificationRecipient | None:
        stmt = (
            select(NotificationRecipient)
            .options(selectinload(NotificationRecipient.notification))
            .where(
                NotificationRecipient.id == recipient_id,
                NotificationRecipient.member_id == member_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_read(self, recipient: NotificationRecipient) -> NotificationRecipient:
        recipient.is_read = True
        recipient.read_at = datetime.now(timezone.utc)
        self.session.add(recipient)
        await self.session.commit()
        await self.session.refresh(recipient)
        return recipient

    async def mark_all_read(self, member_id: UUID) -> None:
        stmt = (
            update(NotificationRecipient)
            .where(
                NotificationRecipient.member_id == member_id,
                NotificationRecipient.is_read.is_(False),
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
        await self.session.commit()


class OutboxRepository:
    """
    Transactional Outbox 저장소.
    enqueue()는 의도적으로 커밋하지 않는다 — 호출부(work/notice/project 서비스 등)의
    기존 트랜잭션에 함께 묶여야 "도메인 변경 성공 + 이벤트 기록 성공"이 원자적으로 보장되기 때문이다.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def enqueue(
        self,
        *,
        event_type: str,
        title: str,
        detail: str | None,
        target_type: int,
        target_id: UUID | None,
        recipient_ids: list[UUID],
    ) -> OutboxEvent:
        event = OutboxEvent(
            event_type=event_type,
            payload={
                "event_type": event_type,
                "title": title,
                "detail": detail,
                "target_type": int(target_type),
                "target_id": str(target_id) if target_id else None,
                "recipient_ids": [str(member_id) for member_id in dict.fromkeys(recipient_ids)],
            },
        )
        self.session.add(event)
        return event

    async def fetch_pending(self, limit: int = 100) -> list[OutboxEvent]:
        """
        FOR UPDATE SKIP LOCKED로 조회 — 릴레이가 여러 인스턴스에서 동시에 떠 있어도
        같은 이벤트를 두 인스턴스가 동시에 집어가지 않는다(한쪽은 잠긴 행을 건너뛴다).
        """
        stmt = (
            select(OutboxEvent)
            .where(OutboxEvent.dispatched.is_(False))
            .order_by(OutboxEvent.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_dispatched(self, event: OutboxEvent) -> None:
        event.dispatched = True
        event.dispatched_at = datetime.now(timezone.utc)
        self.session.add(event)

    async def mark_failed(self, event: OutboxEvent) -> None:
        event.attempts += 1
        self.session.add(event)
