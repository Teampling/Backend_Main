from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Enum, Column
from sqlmodel import Field, Relationship

from app.shared.models.base import BaseModel
from app.shared.enums import MemberRole

if TYPE_CHECKING:
    from app.modules.resource.models import Resource
    from app.modules.favorite.models import Favorite

#dto랑 Model의 차이점: dto는 table=True가 없음. Model은 있음.
class Member(BaseModel, table=True):
    __tablename__ = "members"

    resources: list["Resource"] = Relationship(back_populates="member")
    favorites: list["Favorite"] = Relationship(back_populates="member")

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        description="회원 고유키"
    )

    role: MemberRole = Field(
        default=MemberRole.USER,
        sa_column=Column(
            Enum(
                MemberRole,
                name="memberrole",
                values_callable=lambda x: [e.value for e in x],
            ),
            nullable=False,
        )
    )

    provider: str = Field(
        nullable=False,
        description="OAuth2 제공자"
    )

    provider_id: str | None = Field(
        default=None,
        nullable=True,
        description="OAuth2 고유키"
    )

    email: str = Field(
        unique=True,
        nullable=False,
        description="회원 이메일"
    )

    hashed_password: str | None = Field(
        unique=True,
        default=None,
        nullable=True,
        description="회원 비밀번호"
    )

    name: str = Field(
        nullable=False,
        description="회원 이름"
    )

    birth: date = Field(
        nullable=False,
        description="회원 생년월일"
    )

    gender: bool | None = Field(
        default=None,
        nullable=True,
        description="회원 성별(0: 남, 1: 여, null: 성별을 밝히고 싶지 않음)"
    )

    phone_num: str = Field(
        max_length=20,
        nullable=False,
        description="회원 전화번호"
    )

    nickname: str | None = Field(
        default=None,
        nullable=True,
        description="회원 닉네임"
    )

    organization: str | None = Field(
        default=None,
        nullable=True,
        description="회원 소속"
    )

    dept: str | None = Field(
        default=None,
        nullable=True,
        description="회원 부서"
    )

    profile_url: str | None = Field(
        default=None,
        nullable=True,
        description="프로필 이미지 url"
    )

    detail: str | None = Field(
        default=None,
        nullable=True,
        description="회원 상태 메시지"
    )