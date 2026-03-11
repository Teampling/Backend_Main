from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship

from app.shared.models.base import BaseModel

if TYPE_CHECKING:
    from app.modules.project.models import Project
    from app.modules.member.models import Member

class Resource(BaseModel, table=True):
    __tablename__ = "resources"

    project: "Project" = Relationship(back_populates="resources")
    member: "Member" = Relationship(back_populates="resources")

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        description="자료 고유키"
    )

    project_id: UUID = Field(
        foreign_key="projects.id",
        description="프로젝트 고유키"
    )

    member_id: UUID = Field(
        foreign_key="members.id",
        description="회원 고유키"
    )

    name: str = Field(
        nullable=False,
        description="자료 이름"
    )

    url: str = Field(
        nullable=False,
        description="자료 링크"
    )