from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship

from app.shared.models.base import BaseModel

if TYPE_CHECKING:
    from app.modules.resource.models import Member
    from app.modules.resource.models import Resource
    from app.modules.notice.models import Notice
    from app.modules.work.models import Work
    from app.modules.favorite.models import Favorite

class Project(BaseModel, table=True):
    __tablename__ = "projects"

    leader: "Member" = Relationship(back_populates="projects")
    resources: list["Resource"] = Relationship(back_populates="project")
    notices: list["Notice"] = Relationship(back_populates="project")
    works: list["Work"] = Relationship(back_populates="project")
    favorites: list["Favorite"] = Relationship(back_populates="project")

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        description="프로젝트 고유키"
    )

    leader_id: UUID = Field(
        foreign_key="leader.id",
        description="리더 사용자 고유키"
    )

    name: str = Field(
        nullable=False,
        description="프로젝트 이름"
    )

    start_date: datetime = Field(
        nullable=False,
        description="프로젝트 시작 일자"
    )

    end_date: datetime = Field(
        nullable=False,
        description="프로젝트 종료 일자"
    )

    detail: str | None = Field(
        default=None,
        nullable=True,
        description="프로젝트 상세설명"
    )