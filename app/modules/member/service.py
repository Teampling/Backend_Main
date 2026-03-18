from unittest.mock import patch
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.modules.member.models import Member
from app.modules.member.repository import MemberRepository
from app.modules.member.schemas import MemberCreateIn, MemberUpdateIn


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

    #멤버 수정 서비스(save)
    #여기서의 member_id는 수정을 원하는 회원 id인데 수정할 회원 id가 없으면 안되므로 이렇게 구현.
    async def update(self, member_id: UUID, data: MemberUpdateIn) -> Member:
        member = await self.repository.get_by_id(member_id, include_deleted=False)
        if not member:
            raise AppError.not_found(f"Member[{member_id}")

        #exclude_unset: 코드 작성자가 해당 객체의 값을 지정할 때, 넣지 않은 값은 빼버리는 옵션
        patch = data.model_dump(mode="json", exclude_unset=True)

        #수정할 값인 patch(dictionary 타입임)의 items()를 사용하여 key와 value를 하나하나 가져옴
        #ex)
        #patch = {
        #  "name": "sujin",
        #  "age": 26
        #}
        #for문 첫번째 -> k = "name", v = "sujin"
        #for문 두번째 -> k = "age", v = 26
        #수정할 대상으로 가져온 member의 값을 하나 하나 수정함
        #for문 첫번째 -> member의 k(name)컬럼의 값을 v(sujin)로 변경
        #for문 두번째 -> member의 k(age)컬럼의 값으 v(26)로 변경
        for k, v in patch.items():
            setattr(member, k, v)

        try:
            #아직 commit 안 됨.
            #flush는 save 함수에 있음.
            #하지만 flush() 때문에 INSERT / UPDATE 쿼리는 이미 DB에 날아감
            #DB: 반영됨 (임시)
            #앱: 롤백 가능 상태
            updated = await self.repository.save(member) #member 객체를 DB에 반영 준비
            #이제 롤백 어려움, 트랜잭션 종료됨
            #DB: 확정 저장됨
            await self.session.commit() #진짜 확정 저장
            #refresh 왜 필요할까?
            #DB에서 자동으로 바뀌는 값들이 있음: updated_at, default 값, trigger, DB에서 가공된 값
            #즉, refresh 안 하면 Python 객체는 옛날 값일 수 있음
            await self.session.refresh(updated) #DB 기준 최신 상태 다시 가져오기
            return updated
        #이메일 unique인데 중복 넣었을 때, PK 충돌, FK 깨졌을 때 터짐.
        except IntegrityError:
            #flush 했던 것도 다 되돌림
            #DB: 원래 상태로 복구됨
            await self.session.rollback() #아까 했던 DB 작업 전부 취소
            raise AppError.bad_request(f"[{data.email}]은(는) 이미 존재하는 회원 이메일입니다.")

    # 멤버 삭제 서비스(soft_delete, hard_delete)
    #member를 삭제하는데 hard=True면 진짜 삭제, 아니면 soft delete
    async def delete(self, member_id: UUID, *, hard: bool = False) -> None:
        #삭제된 것이든 아니든 다 가져옴
        #왜냐하면, hard delete 하려면 이미 삭제된 것도 찾아야 하기 때문에
        member = await self.get(member_id, include_deleted=True)

        try:
            if hard:
                #삭제되지 않은 상태면 일단 한 번 막아보기
                if not member.is_deleted:
                    raise AppError.bad_request("삭제되지 않은 회원입니다.")
                await self.repository.hard_delete(member)
            else:
                #이미 삭제된 경우 막기
                if member.is_deleted:
                    raise AppError.bad_request("이미 삭제된 회원입니다.")
                await self.repository.soft_delete(member)
            await self.session.commit() #지금까지 작업 확정 저장

        #문제 생기면 전부 취소하고 다시 에러 던짐
        except Exception:
            await self.session.rollback()
            raise

    #soft_delete 시에 복구하는 서비스
    async def restore(self, member_id: UUID) -> Member:
        #삭제된 회원도 가져와야 복구 가능해서 include_deleted=True
        member = await self.repository.get_by_id(member_id, include_deleted=True)
        #DB에 없으면 끝(존재 여부 체크)
        if not member:
            raise AppError.not_found(f"Member[{member_id}]")
        #삭제된 회원만 복구 가능(삭제 상태 체크)
        if not member.is_deleted:
            raise AppError.bad_request(f"Member[{member_id}]님은 삭제된 상태가 아닙니다.")

        #복구 처리
        try:
            member.is_deleted = False #삭제 상태 해제
            member.deleted_at = None #삭제 시간 제거

            #save 함수에서 add, flush 사용.
            restored = await self.repository.save(member)
            await self.session.commit() #DB에 최종 반영
            await self.session.refresh(restored) #최신 상태 다시 가져오기
            return restored #복구된 객체 반환

        #ex)이메일 unique 충돌, 다른 데이터와 충돌
        #rollback 후 AppError
        except IntegrityError:
            await self.session.rollback()
            raise AppError.bad_request("회원 복구 중 무결성 오류가 발생했습니다.")
        #일반 Exception
        #모든 에러 안전하게 롤백
        except Exception:
            await self.session.rollback()
            raise

