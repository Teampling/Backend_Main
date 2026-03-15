from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.modules.member.models import Member
from app.modules.member.repository import MemberRepository
from app.modules.member.schemas import MemberCreateIn


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

    #멤버 생성 서비스(save)
    async def create(self, data: MemberCreateIn) -> Member:
        existing = await self.repository.get_by_email(data.email) #회원이 이미 있는 경우 가입 불가능하게 하기 위한 작업
        if existing:
            raise AppError.bad_request(f"[{data.email}]은(는) 이미 존재하는 회원 이메일입니다.")

        #dto 타입으로 들어온 데이터를 DB에 넣기 위해 SqlModel에 쓰는 데이터 타입으로 변환
        member = Member(**data.model_dump(mode="json"))
        #pydantic의 dictionary 타입-> SqlModel 타입으로 변경
        #예시!!!
        #data = {
        #   "name": "python",
        #   "level": 3
        #}
        #이런 형태의 dictionary를 SqlModel에서 쓰기 위해서 아래처럼 바꿔줌
        #Skill(name="python", level=3)

        try:
            saved = await self.repository.save(member)
            #커밋은 서비스 단계에서 진행.
            await self.session.commit()
            #서비스 단계에서 DB 데이터 변화가 있을 수 있기 때문에 또 refresh함.
            await self.session.refresh(saved)
            return saved
        #무결성 제약 조건 에러
        #위의 AppError.bad_request 에러 부분과 다른 점은
        #DB에서 unique를 어기는 데이터를 에러 처리할 때 생기는 상황을 위한 이중 처리
        except IntegrityError:
            await self.session.rollback() #무결성을 위반한 데이터는 저장하지 않고 롤백.
            raise AppError.bad_request(f"[{data.email}]은(는) 이미 존재하는 회원 이메일입니다.")

