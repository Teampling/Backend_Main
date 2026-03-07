from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship

from app.shared.models.base import BaseModel

if TYPE_CHECKING:
    from app.modules.project.modules import Project
    from app.modules.member.modules import Member

class Favorite(BaseModel, table=True):
    __tablename__ = "favorites"

    project: "Project" = Relationship(back_populates="favorites")
    member: "Member" = Relationship(back_populates="favorites")

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        description="즐겨찾기 고유키"
    )

    project_id: UUID = Field(
        foreign_key="projects.id",
        description="프로젝트 고유키"
    )

    member_id: UUID = Field(
        foreign_key="members.id",
        description="회원 고유키"
    )