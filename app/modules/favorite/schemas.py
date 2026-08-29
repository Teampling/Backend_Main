from uuid import UUID

from sqlmodel import SQLModel, Field


class FavoriteOut(SQLModel):
    project_id: UUID = Field(description="프로젝트 ID")
    is_favorite: bool = Field(description="즐겨찾기 여부")

    model_config = {
        "json_schema_extra": {
            "example": {
                "project_id": "3e1672cf-8d99-4b1c-9b5e-9c3ece11b089",
                "is_favorite": True,
            }
        }
    }