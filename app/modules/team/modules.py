from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship

from app.shared.models.base import BaseModel

if TYPE_CHECKING:
    from app.modules.project.modules import Project

class Team(BaseModel, table=True):
    __tablename__ = "teams"

    project: "Project" = Relationship(back_populates="teams")

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        description="팀 고유키"
    )

    project_id: UUID = Field(
        foreign_key="projects.id",
        description="프로젝트 고유키"
    )

    name: str = Field(
        nullable=False,
        description="팀 이름"
    )

    detail: str | None = Field(
        default=None,
        nullable=True,
        description="팀 설명"
    )