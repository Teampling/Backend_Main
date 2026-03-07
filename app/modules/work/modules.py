from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import SmallInteger
from sqlmodel import Field, Relationship

from app.shared.models.base import BaseModel

if TYPE_CHECKING:
    from app.modules.project.modules import Project

class Work(BaseModel, table=True):
    __tablename__ = "works"

    project: "Project" = Relationship(back_populates="works")

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        description="작업 고유키"
    )

    project_id: UUID = Field(
        foreign_key="projects.id",
        description="프로젝트 고유키"
    )

    title: str = Field(
        nullable=False,
        description="작업 제목"
    )

    detail: str = Field(
        nullable=False,
        description="작업 내용"
    )

    start_date: datetime = Field(
        nullable=False,
        description="작업 시작 일자"
    )

    end_date: datetime = Field(
        nullable=False,
        description="작업 종료 일자"
    )

    state: int = Field(
        sa_type=SmallInteger,
        nullable=False,
        default=0,
        description="작업 상태(0: 진행예정, 1: 진행중, 2: 완료)"
    )

    priority: int = Field(
        sa_type=SmallInteger,
        nullable=False,
        default=0,
        description="작업 우선순위(0: 낮음, 1: 중간, 2: 높음)"
    )

    remark: str | None = Field(
        default=None,
        nullable=True,
        description="작업 참고정보"
    )

    memo: str | None = Field(
        default=None,
        nullable=True,
        description="작업 메모"
    )