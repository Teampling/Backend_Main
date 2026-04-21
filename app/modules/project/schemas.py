from datetime import datetime
from uuid import UUID

from pydantic import EmailStr
from sqlmodel import SQLModel, Field

from app.modules.member.schemas import MemberOut


class ProjectCreateIn(SQLModel):
    name: str = Field(description="프로젝트 이름")
    start_date: datetime = Field(description="프로젝트 시작 일자")
    end_date: datetime = Field(description="프로젝트 종료 일자")
    detail: str | None = Field(default=None, description="프로젝트 상세설명")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "팀플링",
                "start_date": "2026-02-02",
                "end_date": "2026-05-02",
                "detail": "팀플링 프로젝트 입니다.",
            }
        }
    }

class ProjectUpdateIn(SQLModel):
    name: str = Field(description="프로젝트 이름")
    start_date: datetime | None = Field(default=None, description="프로젝트 시작 일자")
    end_date: datetime | None = Field(default=None, description="프로젝트 종료 일자")
    detail: str | None = Field(default=None, description="프로젝트 상세설명")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "팀플링",
                "start_date": "2026-02-02",
                "end_date": "2026-05-02",
                "detail": "팀플링 프로젝트 입니다.",
            }
        }
    }

class ProjectOut(SQLModel):
    id: UUID = Field(description="프로젝트 ID")
    leader_id: UUID = Field(description="팀장 ID")
    name: str = Field(description="프로젝트 이름")
    start_date: datetime = Field(description="프로젝트 시작 일자")
    end_date: datetime = Field(description="프로젝트 종료 일자")
    detail: str | None = Field(default=None, description="프로젝트 상세설명")
    is_leader: bool = Field(default=False, description="본인이 팀장인지 여부")
    is_member: bool = Field(default=False, description="본인이 프로젝트 멤버(참여자)인지 여부")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "3e1672cf-8d99-4b1c-9b5e-9c3ece11b089",
                "leader_id": "5g1992cf-0h79-1b5d-8m4k-1v6zin11p019",
                "name": "팀플링",
                "start_date": "2026-02-02",
                "end_date": "2026-05-02",
                "detail": "팀플링 프로젝트 입니다.",
                "is_leader": True,
                "is_member": True
            }
        }
    }

class ProjectInviteIn(SQLModel):
    member_id: UUID = Field(description="초대할 회원의 고유 ID")

    model_config = {
        "json_schema_extra": {
            "example": {
                "member_id": "3e1672cf-8d99-4b1c-9b5e-9c3ece11b089"
            }
        }
    }

class ProjectMemberOut(SQLModel):
    member: MemberOut = Field(description="멤버 정보")
    is_leader: bool = Field(description="리더 여부")
    joined_at: datetime = Field(description="프로젝트 합류 일자")

class ProjectInvitationOut(SQLModel):
    id: UUID
    project_id: UUID
    member_id: UUID
    status: str
    expires_at: datetime