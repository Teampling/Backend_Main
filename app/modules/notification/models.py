from uuid import UUID, uuid4

from pydantic import AwareDatetime
from sqlalchemy import SmallInteger, Column, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy_utc import UtcDateTime
from sqlmodel import Field

from app.shared.enums import NotificationEventType
from app.shared.models.base import BaseModel

class Notification(BaseModel, table=True):
    __tablename__ = "notifications"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        description="알림 고유키"
    )

    title: str = Field(
        nullable=False,
        description="알림 제목"
    )

    detail: str = Field(
        nullable=True,
        description="알림 내용"
    )

    event_type: NotificationEventType = Field(
        sa_column=Column(
            Enum(
                NotificationEventType,
                name="notificationeventtype",
                values_callable=lambda x: [e.value for e in x],
            ),
            nullable=False,
        ),
        description="알림 유형"
    )

    target_type: int = Field(
        sa_type=SmallInteger,
        nullable=False,
        default=0,
        description="알림 대상 유형(0: 프로젝트, 1: 작업, 2: 기타)"
    )

    target_id: UUID | None = Field(
        default=None,
        nullable=True,
        description="알림 대상 고유키"
    )

class NotificationRecipient(BaseModel, table=True):
    __tablename__ = "notification_recipients"

    notification_id: UUID = Field(
        foreign_key="notifications.id",
        description="알림 고유키",
        primary_key=True,
    )

    member_id: UUID = Field(
        foreign_key="members.id",
        description="회원 고유키",
        primary_key=True,
    )

    read_at: AwareDatetime | None = Field(
        default=None,
        sa_type=UtcDateTime,
    )

class OutboxEvent(BaseModel, table=True):
    __tablename__ = "outbox_events"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        description="알림 발행 대기함 고유키"
    )

    event_type: NotificationEventType = Field(
        sa_column=Column(
            Enum(
                NotificationEventType,
                name="notificationeventtype",
                values_callable=lambda x: [e.value for e in x],
            ),
            nullable=False,
        ),
        description="알림 유형"
    )

    payload: dict = Field(
        sa_column=Column(JSONB, nullable=False),
        description="발행할 내용 (받는 대상 / 제목 / 본문 등)"
    )

    dispatched: bool = Field(
        default=False,
        description="발행 완료 여부"
    )

    attempts: int = Field(
        default=0,
        description="실패 재시도 횟수 카운트"
    )