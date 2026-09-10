from datetime import datetime
from uuid import UUID

from sqlmodel import SQLModel, Field

from app.modules.notification.models import NotificationRecipient
from app.shared.enums import NotificationEventType


class UnreadCountOut(SQLModel):
    count: int = Field(description="안 읽은 알림 개수")

    model_config = {
        "json_schema_extra": {
            "example": {
                "count": 3
            }
        }
    }


class NotificationOut(SQLModel):
    notification_id: UUID = Field(description="알림 고유키")
    event_type: NotificationEventType = Field(description="알림 유형")
    title: str = Field(description="알림 제목")
    detail: str | None = Field(default=None, description="알림 내용")
    target_type: int = Field(description="알림 대상 유형(0: 프로젝트, 1: 작업, 2: 공지, 3: 초대, 4: 기타)")
    target_id: UUID | None = Field(default=None, description="알림 대상 고유키")
    project_id: UUID | None = Field(default=None, description="알림이 속한 프로젝트 고유키")
    is_read: bool = Field(description="읽음 여부")
    read_at: datetime | None = Field(default=None, description="읽은 시각")
    created_at: datetime = Field(description="생성 일시")

    model_config = {
        "json_schema_extra": {
            "example": {
                "notification_id": "5f1672cf-8d99-4b1c-9b5e-9c3ece11b089",
                "event_type": "notice_created",
                "title": "새 공지가 등록되었습니다.",
                "detail": "공지 상세 내용입니다.",
                "target_type": 2,
                "target_id": "3e1672cf-8d99-4b1c-9b5e-9c3ece11b089",
                "is_read": False,
                "read_at": None,
                "created_at": "2026-09-09T10:00:00Z"
            }
        }
    }

    @classmethod
    def from_recipient(cls, recipient: NotificationRecipient) -> "NotificationOut":
        notification = recipient.notification
        return cls(
            notification_id=notification.id,
            event_type=notification.event_type,
            title=notification.title,
            detail=notification.detail,
            target_type=notification.target_type,
            target_id=notification.target_id,
            project_id=notification.project_id,
            is_read=recipient.read_at is not None,
            read_at=recipient.read_at,
            created_at=notification.created_at,
        )
