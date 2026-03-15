#dto
from datetime import date

from pydantic import HttpUrl, ConfigDict
from sqlmodel import SQLModel


class MemberCreateIn(SQLModel):
    provider: str
    provider_id: str | None
    email: str
    password: str | None
    name: str
    birth: date
    gender: bool | None
    phone_num: str
    nickname: str | None
    organization: str | None
    dept: str | None
    profile_url: HttpUrl | None
    detail: str | None

class MemberUpdateIn(SQLModel):
    password: str | None
    name: str
    birth: date
    gender: bool | None
    phone_num: str
    nickname: str | None
    organization: str | None
    dept: str | None
    profile_url: HttpUrl | None
    detail: str | None

class MemberOut(SQLModel):
    email: str
    name: str
    birth: date
    gender: bool | None
    nickname: str | None
    organization: str | None
    dept: str | None
    profile_url: HttpUrl | None
    detail: str | None

    #SqlModel 타입-> pydantic의 dictionary 타입으로 변경
    #이 함수를 통해 pydantic의 자동 데이터 검증도 가능해짐(router쪽 참고)
    model_config = ConfigDict(from_attributes=True)