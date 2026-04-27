from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Enum, Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.shared.models.base import BaseModel
from app.shared.enums import InvitationStatus

if TYPE_CHECKING:
    from app.modules.member.models import Member
    from app.modules.resource.models import Resource
    from app.modules.notice.models import Notice
    from app.modules.work.models import Work
    from app.modules.favorite.models import Favorite

class ProjectMember(SQLModel, table=True):
    __tablename__ = "project_members"

    project_id: UUID = Field(foreign_key="projects.id", primary_key=True)
    member_id: UUID = Field(foreign_key="members.id", primary_key=True)

    joined_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

class ProjectInvitation(BaseModel, table=True):
    __tablename__ = "project_invitations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.id")
    member_id: UUID = Field(foreign_key="members.id")
    token: str = Field(unique=True, index=True)
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    
    status: InvitationStatus = Field(
        default=InvitationStatus.PENDING,
        sa_column=Column(
            Enum(
                InvitationStatus,
                name="invitationstatus",
                values_callable=lambda x: [e.value for e in x],
            ),
            nullable=False,
        )
    )

class Project(BaseModel, table=True):
    __tablename__ = "projects"

    leader: "Member" = Relationship(
        back_populates="led_projects",
        sa_relationship_kwargs={"primaryjoin": "Project.leader_id == Member.id"}
    )
    members: list["Member"] = Relationship(back_populates="participated_projects", link_model=ProjectMember)
    
    resources: list["Resource"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    notices: list["Notice"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    works: list["Work"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    favorites: list["Favorite"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        description="프로젝트 고유키"
    )

    leader_id: UUID = Field(
        foreign_key="members.id",
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