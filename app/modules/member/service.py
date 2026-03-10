from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.modules.member.modules import Member
from app.modules.member.repository import MemberRepository


class MemberService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = MemberRepository(session)

    #get_by_id의 서비스
    async def get(self, member_id: UUID, *, include_deleted: bool = False) -> Member:
        member = await self.repository.get_by_id(member_id, include_deleted=include_deleted)
        if not member:
            #f"aaa{ddd}": 문자열 aaa 뒤에 변수 ddd의 값을 추가할 수 있는 기능
            raise AppError.not_found(f"Member[{member_id}]")
        return member