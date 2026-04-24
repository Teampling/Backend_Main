from datetime import datetime
from uuid import UUID

from pydantic import model_validator
from sqlmodel import SQLModel, Field
from app.shared.enums import WorkState


class WorkCreateIn(SQLModel):
    project_id: UUID = Field(description="프로젝트 고유키")
    title: str = Field(description="작업 제목")
    detail: str = Field(description="작업 내용")
    start_date: datetime = Field(description="작업 시작 일자")
    end_date: datetime = Field(description="작업 종료 일자")
    state: WorkState = Field(default=WorkState.PLANNED, description="작업 상태(planned, doing, done)")

    @model_validator(mode="after")
    def validate_dates(self) -> "WorkCreateIn":
        if self.start_date > self.end_date:
            raise ValueError("시작일은 종료일보다 빨라야 합니다.")
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "project_id": "3e1672cf-8d99-4b1c-9b5e-9c3ece11b089",
                "title": "작업1",
                "detail": "작업1 입니다.",
                "start_date": "2026-02-02T00:00:00",
                "end_date": "2026-02-07T23:59:59",
                "state": "planned"
            }
        }
    }

class WorkUpdateIn(SQLModel):
    title: str | None = Field(default=None, description="작업 제목")
    detail: str | None = Field(default=None, description="작업 내용")
    start_date: datetime | None = Field(default=None, description="작업 시작 일자")
    end_date: datetime | None = Field(default=None, description="작업 종료 일자")
    state: WorkState | None = Field(default=None, description="작업 상태(planned, doing, done)")

    @model_validator(mode="after")
    def validate_dates(self) -> "WorkUpdateIn":
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValueError("시작일은 종료일보다 빨라야 합니다.")
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "수정된 작업 제목",
                "detail": "수정된 작업 내용",
                "state": "doing"
            }
        }
    }

class WorkOut(SQLModel):
    id: UUID = Field(description="작업 ID")
    project_id: UUID = Field(description="프로젝트 고유키")
    author_id: UUID = Field(description="작성자 고유키")
    title: str = Field(description="작업 제목")
    detail: str = Field(description="작업 내용")
    start_date: datetime = Field(description="작업 시작 일자")
    end_date: datetime = Field(description="작업 종료 일자")
    state: WorkState = Field(description="작업 상태(planned, doing, done)")
    created_at: datetime = Field(description="생성 일시")
    updated_at: datetime | None = Field(default=None, description="수정 일시")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "5f1672kf-8d99-4b1c-9b5e-9c3ece11b089",
                "project_id": "3e1672cf-8d99-4b1c-9b5e-9c3ece11b089",
                "author_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "작업1",
                "detail": "작업1 입니다.",
                "start_date": "2026-02-02T00:00:00",
                "end_date": "2026-02-07T23:59:59",
                "state": "planned",
                "created_at": "2026-04-23T10:00:00"
            }
        }
    }
