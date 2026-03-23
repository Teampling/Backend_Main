from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.sql.annotation import Annotated

from app.core.database import DbSessionDep
from app.core.exceptions import AppError
from app.core.security import decode_token
from app.modules.member.models import Member
from app.modules.member.service import MemberService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/members/login")

async def get_current_member(
        token: Annotated[str, Depends(oauth2_scheme)],
        session: DbSessionDep,
) -> Member:
    try:
        payload = decode_token(token) #decode_token: 복호화
        member_id: str | None = payload.get("sub")
        if member_id is None:
            raise AppError.unauthorized("유효하지 않은 토큰입니다.")

        if payload.get("type") != "access":
            raise AppError.unauthorized("엑세스 토큰이 아닙니다.")

        service = MemberService(session)
        member = await service.get(UUID(member_id))

        if member is None:
            raise AppError.unauthorized("존재하지 않는 사용자입니다.")

        if member.is_deleted:
            raise AppError.unauthorized("삭제된 사용자입니다.")

        return member

    except ValueError as e:
        raise AppError.unauthorized(str(e))
    except Exception:
        raise AppError.unauthorized("인증 과정에서 오류가 발생했습니다.")

CurrentMemberDep = Annotated[Member, Depends(get_current_member)]