#dto
from datetime import date

from pydantic import HttpUrl, ConfigDict
from sqlmodel import SQLModel

#In: 서버 API로 들어오는 데이터(요청)
#Out: 서버 API에서 나가는 데이터(응답)

#In과 Out을 나누는 이유
#요청 데이터와 응답 데이터의 역할이 다르기 때문에 분리한다.
#Member 클래스로 그대로 응답하면 비밀번호 유출 등 보안에 치명적임.
#나누게 되면, 응답에는 password가 없어서 보안에 안전.
#또한, 유지보수에도 편리함.
#나중에 요구사항 바뀌면, 응답에 필드 추가 & 요청 구조 변경 => 서로 영향X

#요청: 일부만 들어와도 됨 (PATCH), 유연해야 함(Optional 많음)
#응답: 항상 일정한 구조, 빠지면 안 됨

#요청
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

#응답
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