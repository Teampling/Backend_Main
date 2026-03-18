#DB 관련 기능
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.modules.member.models import Member


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

    async def get_by_email(self, email: str, *, include_deleted: bool = False) -> Member | None:
        query = select(Member).where(Member.email == email)
        if not include_deleted:
            query = query.where(Member.is_deleted == False)
        return await self.session.scalar(query)

    #flush: 롤백 가능한 상태로 DB에게 SQL을 날리는 함수
    #롤백: SQL문을 없던 거로 돌리는 기능
    #refresh: save(member: Member)에서는 DB에 넣기전에 코드만 짠거라 id값이 없는데,
    #         DB에 add를 하면서 id가 자동 생성된 후의 데이터를 다시 가져오는 기능
    async def save(self, member: Member) -> Member:
        self.session.add(member) #uuid타입의 id가 자동 생성됨
        #커밋 안하고 flush() 사용하는 이유: 커밋은 서비스에서 해야 될 역할이어서
        await self.session.flush()
        await self.session.refresh(member) #데이터를 DB에 저장되어 있는대로 다시 가져옴
        return member

    async def soft_delete(self, member: Member) -> Member:
        member.is_deleted = True
        member.deleted_at = datetime.now(timezone.utc) #아직 DB에 반영 안 됨 (메모리 상태)

        #flush와 commit의 차이
        #flush: DB에 반영, 롤백 가능
        #commit: 최종 저장, 롤백 어려움

        #DB에 지금까지 변경사항 반영해줘(commit은 아님)
        #DB에 UPDATE 쿼리 날림
        await self.session.flush()
        #DB 기준으로 최신 상태 다시 가져와줘
        #refresh 사용 이유: DB에서 자동으로 바뀐 값 반영, 트리거 & default 값 반영
        #refresh 안 하면 위에서 한거 반영 안 됨!!
        await self.session.refresh(member)
        return member #삭제된 상태의 Member 객체 반환

    async def hard_delete(self, member: Member) -> None:
        #이 객체 DB에서 삭제 대상으로 표시한다는 의미
        #밑에 줄만 실행하면 DB에서 삭제 안 되고, 그냥 삭제 예정 상태가 됨.
        await self.session.delete(member)
        #지금까지 변경사항 DB에 반영해줘->진짜 삭제
        await self.session.flush()
        #refresh 대상 없음, None이기에 return도 X



