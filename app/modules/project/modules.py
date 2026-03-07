from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship

from app.shared.models.base import BaseModel

if TYPE_CHECKING:
    from app.modules.team.modules import Team
    from app.modules.resource.modules import Resource
    from app.modules.notice.modules import Notice
    from app.modules.work.modules import Work

class Project(BaseModel, table=True):
    __tablename__ = "projects"

    teams: list["Team"] = Relationship(back_populates="project")
    resources: list["Resource"] = Relationship(back_populates="project")
    notices: list["Notice"] = Relationship(back_populates="project")
    works: list["Work"] = Relationship(back_populates="project")

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        description="프로젝트 고유키"
    )

    leader_id: UUID = Field(
        default_factory=uuid4,
        nullable=False,
        description="팀장 고유키"
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

    img_url: str | None = Field(
        default=None,
        nullable=True,
        description="프로젝트 이미지 url"
    )