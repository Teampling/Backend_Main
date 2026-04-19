from datetime import datetime
from uuid import UUID

from sqlmodel import SQLModel, Field


class WorkCreateIn(SQLModel):
    project_id: UUID = Field(description="프로젝트 고유키")
    title: str | None = Field(default=None, description="작업 제목")
    detail: str | None = Field(default=None, description="작업 내용")
    start_date: datetime = Field(description="작업 시작 일자")
    end_date: datetime = Field(description="작업 종료 일자")
    state: int | None = Field(default=None, description="작업 상태(0: 진행예정, 1: 진행중, 2: 완료)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "project_id": "3e1672cf-8d99-4b1c-9b5e-9c3ece11b089",
                "title": "작업1",
                "detail": "작업1 입니다.",
                "start_date": "2026-02-02",
                "end_date": "2026-02-07",
                "state": "2"
            }
        }
    }

class WorkUpdateIn(SQLModel):
    project_id: UUID = Field(description="프로젝트 고유키")
    title: str | None = Field(default=None, description="작업 제목")
    detail: str | None = Field(default=None, description="작업 내용")
    start_date: datetime = Field(description="작업 시작 일자")
    end_date: datetime = Field(description="작업 종료 일자")
    state: int | None = Field(default=None, description="작업 상태(0: 진행예정, 1: 진행중, 2: 완료)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "project_id": "3e1672cf-8d99-4b1c-9b5e-9c3ece11b089",
                "title": "작업1",
                "detail": "작업1 입니다.",
                "start_date": "2026-02-02",
                "end_date": "2026-02-07",
                "state": "2"
            }
        }
    }

class WorkOut(SQLModel):
    id: UUID = Field(description="작업 ID")
    project_id: UUID = Field(description="프로젝트 고유키")
    title: str | None = Field(default=None, description="작업 제목")
    detail: str | None = Field(default=None, description="작업 내용")
    start_date: datetime = Field(description="작업 시작 일자")
    end_date: datetime = Field(description="작업 종료 일자")
    state: int | None = Field(default=None, description="작업 상태(0: 진행예정, 1: 진행중, 2: 완료)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "5f1672kf-8d99-4b1c-9b5e-9c3ece11b089",
                "project_id": "3e1672cf-8d99-4b1c-9b5e-9c3ece11b089",
                "title": "작업1",
                "detail": "작업1 입니다.",
                "start_date": "2026-02-02",
                "end_date": "2026-02-07",
                "state": "2"
            }
        }
    }