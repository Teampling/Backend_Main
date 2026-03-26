from base64 import decode
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.security import password_hash, verify_password, create_access_token, create_refresh_token, decode_token
from app.modules.member.models import Member
from app.modules.member.repository import MemberRepository
from app.modules.member.schemas import MemberCreateIn, MemberUpdateIn
from app.shared.enums import ProviderType


#pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") #비밀번호 해쉬화

class MemberService:
    def __init__(self, session: AsyncSession, repository: MemberRepository):
        self.session = session
        self.repository = repository

    #get_by_id의 서비스
    async def get(self, member_id: UUID, *, include_deleted: bool = False) -> Member:
        member = await self.repository.get_by_id(member_id, include_deleted=include_deleted)
        if not member:
            #f"aaa{ddd}": 문자열 aaa 뒤에 변수 ddd의 값을 추가할 수 있는 기능
            raise AppError.not_found(f"Member[{member_id}]")
        return member

    #list, count 서비스 부분
    #연결: Service(page, size) -> offset 계산 ->
    #-> Repository(offset, limit) -> DB에서 조회
    #사용자 요청을 받아서 repository에 맞게 변환
    async def list(
            self,
            *,
            keyword: str | None = None,
            page: int = 1, #기본값
            size: int = 50, #기본값
            include_deleted: bool = False,
    ) -> dict[str, Any]:
        #문자열로 된 이름(key)을 쓰고 그 안에는 아무 데이터(value)를 넣을 수 있는 자료구조(딕셔너리)
        #dict[str, Any] = key는 str, value는 Any인 dict

        #페이지는 1부터 시작해야 하니까 0, -1 들어오면 1로 바꿔줌
        if page < 1:
            page = 1
        #한 번에 가져오는 데이터 수 제한
        #너무 적으면 1개로, 너무 많으면 100개로 제한
        if size < 1:
            size = 1
        if size > 100:
            size = 100

        #page는 1부터 시작!! offset은 0부터 시작!!
        #ex) page= 1, size= 50
        #offset = (1-1)*50 = 0
        #즉, 0번부터 가져옴, 1~50번째 데이터
        offset = (page - 1) * size

        #repository.list 호출 => repository가 하는 일: 실제 DB에서 데이터 가져오기
        #items: 실제 데이터 목록, repository의 list()에서 가져온 결과
        #현재 페이지에 해당하는 데이터들
        #즉, 사용자에게 보여줄 데이터
        items = await self.repository.list(
            keyword=keyword,
            offset=offset,
            limit=size,
            include_deleted=include_deleted,
        )
        #total: 전체 데이터 개수, repository의 count()에서 가져온 값
        #즉, 조건에 맞는 전체 데이터 수
        total = await self.repository.count(
            keyword=keyword,
            include_deleted=include_deleted,
        )
        #이 4개가 세트! 위에 설명 참고!
        return {
            "items": items,
            "page": page,
            "size": size,
            "total": total
        }

    #멤버 생성 서비스(save)
    async def create(self, data: MemberCreateIn) -> Member:
        existing = await self.repository.get_by_email(data.email) #회원이 이미 있는 경우 가입 불가능하게 하기 위한 작업
        if existing:
            raise AppError.bad_request(f"[{data.email}]은(는) 이미 존재하는 회원 이메일입니다.")

        #dto 타입으로 들어온 데이터를 DB에 넣기 위해 SqlModel에 쓰는 데이터 타입으로 변환
        #member = Member(**data.model_dump(mode="json")) #이대로 저장하면 데이터 안에 있는 password가 그대로 들어가서 보안 문제 생김
        member = Member(
            **data.model_dump(exclude={"password", "profile_url"}),
            #enum 타입으로 shared.enums.py 안에 적어놓음. 오타 방지를 위해서 & 수정도 쉽게 하기 위해서
            profile_url=str(data.profile_url) if data.profile_url is not None else None,
            provider=ProviderType.LOCAL,
            provider_id=None, #소셜 로그인이 아니어서
            hashed_password=password_hash(data.password)
        )
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
    async def update(self, target_member_id: UUID, actor_member_id: UUID, data: MemberUpdateIn) -> Member:
        if actor_member_id != target_member_id:
            raise AppError.forbidden("본인 정보만 수정할 수 있습니다.")

        member = await self.repository.get_by_id(target_member_id, include_deleted=False)
        if not member:
            raise AppError.not_found(f"Member[{target_member_id}")

        #exclude_unset: 코드 작성자가 해당 객체의 값을 지정할 때, 넣지 않은 값은 빼버리는 옵션
        patch = data.model_dump( #patch: 수정할 데이터
            exclude={"password"},
            exclude_unset=True,
        )

        #이 둘은 DB에 넣기 전 특수한 처리를 해줘야 해서 따로 빼서 처리.
        if "profile_url" in patch and patch["profile_url"] is not None:
            patch["profile_url"] = str(patch["profile_url"]) #profile_url 수정값을 문자열로 강제 형변환

        if data.password is not None:
            patch["hashed_password"] = password_hash(data.password)

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
    async def delete(self, target_member_id: UUID, actor_member_id: UUID, *, hard: bool = False) -> None:
        if actor_member_id != target_member_id:
            raise AppError.forbidden("본인 정보만 삭제할 수 있습니다.")

        #삭제된 것이든 아니든 다 가져옴
        #왜냐하면, hard delete 하려면 이미 삭제된 것도 찾아야 하기 때문에
        member = await self.get(target_member_id, include_deleted=True)

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

    #로그인 함수
    async def login(self, email: str, password: str) -> dict[str, str]:
        member = await self.repository.get_by_email(email)

        #사용자가 없거나 soft_delete 된 상태면 로그인을 막아야 함.
        if not member or member.is_deleted:
            raise AppError.unauthorized("이메일 또는 비밀번호가 일치하지 않습니다.")

        #소셜 로그인 한 사용자는 password가 null이기 때문에 사용자들을 일반 로그인하지 못하게 한다.
        if not member.hashed_password:
            raise AppError.unauthorized("소셜 로그인 계정입니다. 해당 서비스로 로그인 하세요.")

        if not verify_password(plain_password=password, hashed_password=member.hashed_password):
            raise AppError.bad_request("비밀번호가 틀렸습니다.")

        return {
            "access_token": create_access_token(data=str(member.id)),
            "refresh_token": create_refresh_token(data=str(member.id)),
        }

    #accessToken 재발급 함수
    async def reissue(self, refresh_token: str) -> dict[str, str]:
        try:
            payload = decode_token(refresh_token)
            member_id: str | None = payload.get("sub")
            token_type: str | None = payload.get("type")

            if member_id is None or token_type != "refresh":
                raise AppError.unauthorized("유효하지 않은 refresh 토큰입니다.")

            member = await self.get(UUID(member_id))
            if not member or member.is_deleted:
                raise AppError.unauthorized("존재하지 않거나 삭제된 사용자입니다.")

            return {
                "access_token": create_access_token(data=str(member.id)),
                "refresh_token": create_refresh_token(data=str(member.id)),
            }
        except ValueError as e:
            raise AppError.unauthorized(str(e))
        except Exception as e:
            raise AppError.unauthorized(f"토큰 재발급 과정에서 오류가 발생했습니다.: {str(e)}")

