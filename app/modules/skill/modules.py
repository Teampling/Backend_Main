from uuid import UUID, uuid4

from pydantic import HttpUrl
from sqlmodel import Field

from app.shared.models.base import BaseModel


class Skill(BaseModel, table=True):
    __tablename__ = "skills"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        description="스킬 고유키"
    )

    img_url: HttpUrl = Field(
        nullable=False,
        description="스킬 이미지 url"
    )

    name: str = Field(
        unique=True,
        nullable=False,
        description="스킬 이름"
    )
