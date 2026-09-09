from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.modules.notification.repository import NotificationRepository


class NotificationService:
    def __init__(self, session: AsyncSession, repository: NotificationRepository):
        self.session = session
        self.repository = repository

    async def list_by_member(
            self,
            member_id: UUID,
            *,
            page: int = 1,
            size: int = 50,
            unread_only: bool = False,
    ) -> dict[str, Any]:
        offset = (page - 1) * size
        items = await self.repository.list_by_member(
            member_id,
            offset=offset,
            limit=size,
            unread_only=unread_only,
        )
        total = await self.repository.count_by_member(
            member_id,
            unread_only=unread_only,
        )
        return {
            "items": items,
            "page": page,
            "size": size,
            "total": total,
        }

    async def count_unread(self, member_id: UUID) -> int:
        return await self.repository.count_by_member(member_id, unread_only=True)

    async def mark_read(self, member_id: UUID, notification_id: UUID) -> None:
        recipient = await self.repository.get_recipient(member_id, notification_id)
        if recipient is None:
            raise AppError.not_found(f"[{notification_id}] 알림")

        if recipient.read_at is None:
            recipient.read_at = datetime.now(timezone.utc)

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def mark_all_read(self, member_id: UUID) -> int:
        try:
            count = await self.repository.mark_all_read(member_id)
            await self.session.commit()
            return count
        except Exception:
            await self.session.rollback()
            raise
