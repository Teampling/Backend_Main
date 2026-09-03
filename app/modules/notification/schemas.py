from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.modules.notification.models import NotificationRecipient


class NotificationOut(BaseModel):
    id: UUID  # 회원별 수신함(NotificationRecipient) id — 읽음 처리 API가 이 값을 사용한다.
    notification_id: UUID
    event_type: str | None
    title: str
    detail: str | None
    target_type: int
    target_id: UUID | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime

    @classmethod
    def from_recipient(cls, recipient: NotificationRecipient) -> "NotificationOut":
        notification = recipient.notification
        return cls(
            id=recipient.id,
            notification_id=notification.id,
            event_type=notification.event_type,
            title=notification.title,
            detail=notification.detail,
            target_type=notification.target_type,
            target_id=notification.target_id,
            is_read=recipient.is_read,
            read_at=recipient.read_at,
            created_at=recipient.created_at,
        )


class UnreadCountOut(BaseModel):
    count: int
