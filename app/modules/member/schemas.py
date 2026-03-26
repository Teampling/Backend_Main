#dto
from datetime import date
from uuid import UUID

from pydantic import HttpUrl, ConfigDict, EmailStr
from sqlmodel import SQLModel, Field


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
    email: EmailStr = Field(description="회원 이메일")
    password: str = Field(description="비밀번호")
    name: str = Field(description="이름")
    birth: date = Field(description="생년월일")
    gender: bool | None = Field(default=None, description="성별")
    phone_num: str = Field(description="전화번호")
    nickname: str | None = Field(default=None, description="닉네임")
    organization: str | None = Field(default=None, description="소속")
    dept: str | None = Field(default=None, description="부서")
    profile_url: HttpUrl | None = Field(default=None, description="프로필 이미지 URL")
    detail: str | None = Field(default=None, description="상세 소개")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "test@naver.com",
                "password": "test1234!",
                "name": "송시월",
                "birth": "2001-05-21",
                "gender": True,
                "phone_num": "01012345678",
                "nickname": "쏴리쏭",
                "organization": "한성대학교",
                "dept": "컴퓨터공학과",
                "profile_url": "https://example.com/profile.jpg",
                "detail": "안녕하세요!"
            }
        }
    }

class MemberUpdateIn(SQLModel):
    password: str | None = Field(default=None, description="비밀번호")
    name: str | None = Field(default=None, description="이름")
    birth: date | None = Field(default=None, description="생년월일")
    gender: bool | None = Field(default=None, description="성별")
    phone_num: str | None = Field(default=None, description="전화번호")
    nickname: str | None = Field(default=None, description="닉네임")
    organization: str | None = Field(default=None, description="소속")
    dept: str | None = Field(default=None, description="부서")
    profile_url: HttpUrl | None = Field(default=None, description="프로필 이미지 URL")
    detail: str | None = Field(default=None, description="상세 소개")

    model_config = {
        "json_schema_extra": {
            "example": {
                "password": "test1234!",
                "name": "송시월",
                "birth": "2001-05-21",
                "gender": True,
                "phone_num": "01012345678",
                "nickname": "쏴리쏭",
                "organization": "한성대학교",
                "dept": "컴퓨터공학과",
                "profile_url": "https://example.com/profile.jpg",
                "detail": "안녕하세요!"
            }
        }
    }

#응답
class MemberOut(SQLModel):
    id: UUID = Field(description="회원 ID")
    email: EmailStr = Field(description="회원 이메일")
    name: str = Field(description="이름")
    birth: date = Field(description="생년월일")
    gender: bool | None = Field(default=None, description="성별")
    nickname: str | None = Field(default=None, description="닉네임")
    organization: str | None = Field(default=None, description="소속")
    dept: str | None = Field(default=None, description="부서")
    profile_url: HttpUrl | None = Field(default=None, description="프로필 이미지 URL")
    detail: str | None = Field(default=None, description="상세 소개")

    #SqlModel 타입-> pydantic의 dictionary 타입으로 변경
    #이 함수를 통해 pydantic의 자동 데이터 검증도 가능해짐(router쪽 참고)
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "3e1672cf-8d99-4b1c-9b5e-9c3ece11b089",
                "email": "test@example.com",
                "name": "송시월",
                "birth": "2001-05-21",
                "gender": True,
                "nickname": "쏴리쏭",
                "organization": "한성대학교",
                "dept": "컴퓨터공학과",
                "profile_url": "https://example.com/profile.jpg",
                "detail": "안녕하세요!"
            }
        }
    )

#토큰 응답용 dto
class TokenOut(SQLModel):
    access_token: str = Field(description="액세스 토큰 (JWT)")
    refresh_token: str = Field(description="리프레시 토큰 (JWT)")
    # Bearer: Api가 인증 과정을 거칠 때 jwt token을 사용하도록 약속한 타입
    token_type: str = Field(default="Bearer", description="토큰 타입")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer"
            }
        }
    )