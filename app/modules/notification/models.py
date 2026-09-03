from datetime import datetime
from typing import Any, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import SmallInteger, Column, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy_utc import UtcDateTime
from sqlmodel import Field, Relationship

from app.shared.models.base import BaseModel

if TYPE_CHECKING:
    pass


class Notification(BaseModel, table=True):
    __tablename__ = "notifications"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        description="알림 고유키"
    )

    event_type: str | None = Field(
        default=None,
        nullable=True,
        index=True,
        description="발생시킨 이벤트 종류 (예: notice.created, project.invited)"
    )

    title: str = Field(
        nullable=False,
        description="알림 제목"
    )

    detail: str = Field(
        nullable=True,
        description="알림 내용"
    )

    target_type: int = Field(
        sa_type=SmallInteger,
        nullable=False,
        default=0,
        description="알림 대상 유형(0: 프로젝트, 1: 작업, 2: 기타, 3: 공지, 4: 초대)"
    )

    target_id: UUID | None = Field(
        default=None,
        nullable=True,
        description="알림 대상 고유키"
    )

    recipients: list["NotificationRecipient"] = Relationship(
        back_populates="notification",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class NotificationRecipient(BaseModel, table=True):
    """
    알림 1건(Notification)을 실제로 받는 회원별 수신함.
    이벤트 하나가 여러 명에게 팬아웃될 수 있기 때문에(예: 공지 등록 시 프로젝트 멤버 전원),
    "누가 읽었는지"는 Notification이 아니라 회원별 행에서 따로 관리한다.
    """
    __tablename__ = "notification_recipients"
    __table_args__ = (
        UniqueConstraint("notification_id", "member_id", name="uq_notification_recipient_member"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)

    notification_id: UUID = Field(foreign_key="notifications.id", nullable=False, index=True)
    member_id: UUID = Field(foreign_key="members.id", nullable=False, index=True)

    is_read: bool = Field(
        default=False,
        nullable=False,
        sa_column_kwargs={"server_default": "false"},
        description="읽음 여부"
    )
    read_at: datetime | None = Field(default=None, nullable=True, sa_type=UtcDateTime)

    notification: Notification = Relationship(back_populates="recipients")


class OutboxEvent(BaseModel, table=True):
    """
    Transactional Outbox.
    도메인 서비스(notice, project, work 등)는 자신의 트랜잭션 안에서 이 테이블에 이벤트를 기록하기만 한다.
    실제 메시지 브로커(Redis Stream) 발행은 별도 프로세스(outbox_relay)가 폴링하며 담당하므로,
    "도메인 데이터 커밋"과 "이벤트 발행 기록"이 하나의 트랜잭션으로 묶여 원자성이 보장된다.
    (브로커가 잠시 죽어도 이벤트가 유실되지 않고, 다음 폴링에서 재시도된다 — at-least-once)
    """
    __tablename__ = "outbox_events"

    id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)

    event_type: str = Field(nullable=False, index=True, description="이벤트 종류 (예: notice.created)")

    payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
        description="브로커로 그대로 발행될 이벤트 본문"
    )

    dispatched: bool = Field(
        default=False,
        nullable=False,
        index=True,
        sa_column_kwargs={"server_default": "false"},
        description="Redis Stream으로 발행 완료 여부"
    )
    dispatched_at: datetime | None = Field(default=None, nullable=True, sa_type=UtcDateTime)

    attempts: int = Field(
        default=0,
        nullable=False,
        sa_type=Integer,
        sa_column_kwargs={"server_default": "0"},
        description="발행 시도 횟수 (실패 시 증가)"
    )
