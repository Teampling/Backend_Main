from datetime import datetime
from uuid import UUID

from sqlmodel import SQLModel, Field


class NoticeCreateIn(SQLModel):
    project_id: UUID = Field(description="프로젝트 고유키")
    title: str = Field(description="공지 제목")
    detail: str = Field(description="공지 상세 내용")

    model_config = {
        "json_schema_extra": {
            "example": {
                "project_id": "3e1672cf-8d99-4b1c-9b5e-9c3ece11b089",
                "title": "공지사항 제목",
                "detail": "공지사항 상세 내용입니다."
            }
        }
    }


class NoticeUpdateIn(SQLModel):
    title: str | None = Field(default=None, description="공지 제목")
    detail: str | None = Field(default=None, description="공지 상세 내용")

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "수정된 공지 제목",
                "detail": "수정된 공지 상세 내용"
            }
        }
    }


class NoticeOut(SQLModel):
    id: UUID = Field(description="공지 ID")
    project_id: UUID = Field(description="프로젝트 고유키")
    title: str = Field(description="공지 제목")
    detail: str = Field(description="공지 상세 내용")
    created_at: datetime = Field(description="생성 일시")
    updated_at: datetime | None = Field(default=None, description="수정 일시")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "5f1672kf-8d99-4b1c-9b5e-9c3ece11b089",
                "project_id": "3e1672cf-8d99-4b1c-9b5e-9c3ece11b089",
                "title": "공지사항 제목",
                "detail": "공지사항 상세 내용입니다.",
                "created_at": "2026-04-27T10:00:00"
            }
        }
    }
