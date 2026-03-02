from pydantic import HttpUrl
from sqlmodel import SQLModel, Field


class SkillCreateIn(SQLModel):
    name: str
    img_url: HttpUrl

class SkillUpdateIn(SQLModel):
    name: str | None = None
    img_url: HttpUrl | None = None