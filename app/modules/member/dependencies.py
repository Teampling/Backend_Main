from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.database import DbSessionDep
from app.core.exceptions import AppError
from app.core.security import decode_token
from app.modules.member.models import Member
from app.modules.member.repository import MemberRepository
from app.modules.member.service import MemberService


#전체 흐름
#Client -> HTTP 요청 -> Router -> Service -> Repository -> DB

#MemberService를 모든 Member api 함수들에게 의존성 주입을 하기 위한 과정
def get_member_service(session: DbSessionDep) -> MemberService:
    repository = MemberRepository(session)
    return MemberService(session, repository)

#get_member_service() 실행하고 MemberService 만들어서 service에 넣어줘
MemberServiceDep = Annotated[MemberService, Depends(get_member_service)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/members/login")

async def get_current_member(
        service: MemberServiceDep,
        token: Annotated[str, Depends(oauth2_scheme)],
) -> Member:
    try:
        payload = decode_token(token) #decode_token: 복호화
        member_id: str | None = payload.get("sub")
        if member_id is None:
            raise AppError.unauthorized("유효하지 않은 토큰입니다.")

        if payload.get("type") != "access":
            raise AppError.unauthorized("엑세스 토큰이 아닙니다.")

        member = await service.get(UUID(member_id), include_deleted=True)

        if member is None:
            raise AppError.unauthorized("존재하지 않는 사용자입니다.")

        if member.is_deleted:
            raise AppError.unauthorized("삭제된 사용자입니다.")

        return member

    except ValueError as e:
        raise AppError.unauthorized(str(e))
    except Exception as e:
        raise AppError.unauthorized(f"인증 과정에서 오류가 발생했습니다.: {str(e)}")

CurrentMemberDep = Annotated[Member, Depends(get_current_member)]