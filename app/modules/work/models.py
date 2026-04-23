from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Enum, Column
from sqlmodel import Field, Relationship

from app.shared.models.base import BaseModel
from app.shared.enums import WorkState

if TYPE_CHECKING:
    from app.modules.project.models import Project
    from app.modules.member.models import Member

class Work(BaseModel, table=True):
    __tablename__ = "works"

    project: "Project" = Relationship(back_populates="works")
    author: "Member" = Relationship(back_populates="created_works")

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

    author_id: UUID = Field(
        foreign_key="members.id",
        description="작성자 고유키"
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

    state: WorkState = Field(
        default=WorkState.PLANNED,
        sa_column=Column(
            Enum(
                WorkState,
                name="workstate",
                values_callable=lambda x: [e.value for e in x],
            ),
            nullable=False,
        ),
        description="작업 상태(planned: 진행예정, doing: 진행중, done: 완료)"
    )