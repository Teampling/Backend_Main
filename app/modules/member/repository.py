#DB 관련 기능
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.modules.member.modules import Member


class MemberRepository:
    #생성자
    #self= 자기 자신을 나타내는 변수, 기본적으로 파이썬 내에 있음
    #여기에서 self는 MemberRepository 클래스 본인
    def __init__(self, session: AsyncSession):
        self.session = session

    #여기에서 self는 get_by_id
    #include_deleted가 true면 soft 삭제 된 Member도 조회 가능, False면 조회 불가
    #* 뒤에 있는 인자들은 함수를 사용할 때 인자명까지 같이 써줘야 함
    #ex) plus(a, *, b) 함수를 사용할 떄 plus(1, b=2) 이런 식으로 써야 함
    #함수의 -> 뒤에는 그 함수의 리턴 객체를 넣는다
    async def get_by_id(self, member_id: UUID, *, include_deleted: bool = False) -> Member | None:
        query = select(Member).where(Member.id == member_id)
        #include_deleted가 False면 where절을 통해 soft 삭제 된 데이터를 제외해줘야 함
        if not include_deleted:
            query = query.where(Member.is_deleted == False)
        #scalar= session 기능임, 코드로 만든 쿼리를 DB로 보내 결과값을 받는다
        return await self.session.scalar(query)