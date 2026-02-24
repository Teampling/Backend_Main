from uuid import UUID, uuid4

from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from sqlmodel import SQLModel, Field

from app.shared.models.base import BaseModel


class Skill(BaseModel, table=True):
    __tablename__ = "skills"

    id: UUID = Field(default_factory=uuid4,
                     primary_key=True,
                     sa_type=PG_UUID(as_uuid=True),
                     )
    img_url: str = Field(description="스킬 이미지 url")
    name: str = Field(description="스킬 이름")
