from uuid import UUID

from pydantic import HttpUrl, ConfigDict, Field
from sqlmodel import SQLModel


class SkillCreateIn(SQLModel):
    name: str = Field(
        description="스킬 이름",
        examples=["Java"],
    )

class SkillUpdateIn(SQLModel):
    name: str | None = Field(
        description="스킬 이름",
        examples=["Java"],
    )

class SkillOut(SQLModel):
    id: UUID
    name: str
    img_url: HttpUrl

    model_config = ConfigDict(from_attributes=True)