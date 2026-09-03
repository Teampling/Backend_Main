from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.modules.notification.models import NotificationRecipient
from app.modules.notification.repository import NotificationRepository


class NotificationService:
    def __init__(self, session: AsyncSession, repository: NotificationRepository):
        self.session = session
        self.repository = repository

    async def list(
        self,
        member_id: UUID,
        *,
        page: int = 1,
        size: int = 20,
        unread_only: bool = False,
    ) -> dict:
        items = await self.repository.list_for_member(member_id, page=page, size=size, unread_only=unread_only)
        total = await self.repository.count_for_member(member_id, unread_only=unread_only)
        return {"items": items, "page": page, "size": size, "total": total}

    async def unread_count(self, member_id: UUID) -> int:
        return await self.repository.count_for_member(member_id, unread_only=True)

    async def mark_read(self, recipient_id: UUID, member_id: UUID) -> NotificationRecipient:
        recipient = await self.repository.get_recipient(recipient_id, member_id)
        if not recipient:
            raise AppError.not_found("알림")

        if recipient.is_read:
            return recipient

        return await self.repository.mark_read(recipient)

    async def mark_all_read(self, member_id: UUID) -> None:
        await self.repository.mark_all_read(member_id)
