from uuid import UUID, uuid4

from sqlalchemy import SmallInteger
from sqlmodel import Field

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

    target_type: int = Field(
        sa_type=SmallInteger,
        nullable=False,
        default=0,
        description="알림 대상 유형(0: 낮음, 1: 중간, 2: 높음)"
    )

    target_id: UUID | None = Field(
        default_factory=uuid4,
        primary_key=True,
        default=None,
        nullable=True,
        description="알림 대상 고유키"
    )