#DB 관련 기능
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

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

    #list() = 회원 데이터 보여주기
    #count() = 회원 총 몇 명인지 알려주기
    #회원 목록을 검색 + 정렬 + 페이지 나눠서 가져오는 함수
    async def list(
            self,
            *,
            #검색어가 있을 수도 없을 수도..
            #값 있으면 검색, 값 없으면(None) 전체 조회
            keyword: str | None = None,
            #몇 개 건너뛸지, 스킵(페이지 시작)
            #0번째부터 시작(처음부터 시작)
            offset: int = 0,
            #최대 몇 개까지 가져올지(페이지 크기)
            #한 번에 최대 100개까지 조회
            limit: int = 100,
            #삭제된 회원 포함 여부, 기본적으로 삭제된 회원은 포함X
            include_deleted: bool = False,
    ) -> list[Member]: #리스트로 나옴
        #SQL 느낌
        #SELECT * FROM member와 같은 뜻
        #아직 실행X, 회원 다 가져올 준비..
        stmt = select(Member)

        if keyword:
            #Member.name(이름)에 keyword가 포함된 회원만 찾으라는 뜻
            #ilike: 대소문자 구분 없이 검색

            #f"": 변수 값을 문자열에 넣는 문법
            #ex) keyword = "python" f"{keyword}" => 결과: "python"
            #keyword%: keyword로 시작, %keyword: keyword로 끝, %keyword%: keyword 포함
            stmt = stmt.where(Member.name.ilike(f"%{keyword}%")) #"keyword" 포함(대소문자 구분X)
        #삭제된 회원을 숨길지 말지 정하는 코드
        #include_deleted는 기본값이 false인데 not이 붙었으므로 true가 됨.
        #false일 때 조건문이 실행X, true일 때 조건문 실행(파이썬 문법)
        if not include_deleted: #삭제된 거 안 보여줄 거면
            stmt = stmt.where(Member.is_deleted == False) #삭제 안 된 애들만 가져와

        #정렬 & 페이지
        #order_by, asc: 이름 오름차순으로 정렬
        #offset: 앞에서부터 몇 개 건너뜀(스킵)
        #limit: 몇 개 가져올지 제한
        #ex) offset = 0, limit = 10 => 1~10번째 회원
        #ex) offset = 10, limit = 10 => 11~20번째 회원
        stmt = stmt.order_by(Member.name.asc()).offset(offset).limit(limit)
        #실행!!
        #scalars(): Member 객체만 꺼냄
        #.all(): 리스트로 반환
        #결과: [Member(), Member(), Member()]
        return (await self.session.scalars(stmt)).all()

    #list 함수는 데이터 가져오기(총 몇 개인지 모름..=> 회원 명 수는 알아도 페이지 수를 모름)
    #count 함수는 페이지 수 계산
    async def count(
            self,
            *,
            keyword: str | None = None,
            include_deleted: bool = False) -> int: #숫자로 나옴
        #SELECT COUNT(*) FROM member 느낌..
        stmt = select(func.count()).select_from(Member)

        #list랑 count는 조건이 완전히 같아야 페이지가 맞아서 조건 부분이 동일.
        if keyword:
            stmt = stmt.where(Member.name.ilike(f"%{keyword}%"))

        if not include_deleted:
            stmt = stmt.where(Member.is_deleted == False)

        #scalar(): 숫자 하나 가져옴
        #or 0: 값 없으면 0
        #int(): 정수로 변환
        return int(await self.session.scalar(stmt) or 0) #숫자로 출력

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
