from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship

from app.shared.models.base import BaseModel

if TYPE_CHECKING:
    from app.modules.project.models import Project

class Notice(BaseModel, table=True):
    __tablename__ = "notices"

    project: "Project" = Relationship(back_populates="notices")

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        description="공지 고유키"
    )

    project_id: UUID = Field(
        foreign_key="projects.id",
        description="프로젝트 고유키"
    )

    title: str = Field(
        nullable=False,
        description="공지 제목"
    )

    detail: str = Field(
        nullable=False,
        description="공지 내용"
    )