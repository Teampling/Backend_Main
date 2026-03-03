from uuid import UUID

from pydantic import HttpUrl, ConfigDict
from sqlmodel import SQLModel, Field


class SkillCreateIn(SQLModel):
    name: str
    img_url: HttpUrl

class SkillUpdateIn(SQLModel):
    name: str | None = None
    img_url: HttpUrl | None = None

class SkillOut(SQLModel):
    id: UUID
    name: str
    img_url: HttpUrl

    model_config = ConfigDict(from_attributes=True)