from uuid import UUID

from pydantic import HttpUrl, ConfigDict
from sqlmodel import SQLModel, Field


class SkillCreateIn(SQLModel):
    name: str
    img_url: HttpUrl

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Java",
                "img_url": "https://example.com/skills/java.png"
            }
        }
    }

class SkillUpdateIn(SQLModel):
    name: str | None = None
    img_url: HttpUrl | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Java",
                "img_url": "https://example.com/skills/java.png"
            }
        }
    }

class SkillOut(SQLModel):
    id: UUID
    name: str
    img_url: HttpUrl

    model_config = ConfigDict(from_attributes=True)