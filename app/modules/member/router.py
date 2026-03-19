#resolver
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query, Depends, status

from app.core.database import DbSessionDep
from app.modules.member.schemas import MemberCreateIn, MemberOut, MemberUpdateIn
from app.modules.member.service import MemberService
from app.shared.schemas import ApiResponse, PageOut


#전체 흐름
#Client -> HTTP 요청 -> Router -> Service -> Repository -> DB

#MemberService를 모든 Member api 함수들에게 의존성 주입을 하기 위한 과정
def get_member_service(session: DbSessionDep) -> MemberService:
    return MemberService(session)

#get_member_service() 실행하고 MemberService 만들어서 service에 넣어줘
MemberServiceDep = Annotated[MemberService, Depends(get_member_service)]

#prefix: 앞에 공통적으로 들어갈 경로명
#tags: Swagger에서 API를 분류할 때 사용하는 것
router = APIRouter(prefix="/members", tags=["Member"])

#회원 목록 조회 API를 만드는 코드
@router.get(
    path="",
    #응답 구조: ApiResponse - data: PageOut - items: MemberOut 리스트
    response_model=ApiResponse[PageOut[MemberOut]],
    summary="회원 목록 조회",
    description="키워드, 페이지, 사이즈 조건으로 회원 목록을 조회합니다.",
)
async def list_members(
        service: MemberServiceDep,
        keyword: Annotated[str | None, Query(description="검색 키워드", example="수진")] = None,
        #ge: 이상, le: 이하
        page: Annotated[int,Query(ge=1, description="페이지 번호")] = 1,
        size: Annotated[int, Query(ge=1, le=100, description="페이지 크기")] = 50,
        include_deleted: Annotated[bool, Query(description="soft delete된 데이터 포함 여부")] = False,
):
    result = await service.list(
        keyword=keyword,
        page=page,
        size=size,
        include_deleted=include_deleted,
    )

    #응답 만드는 부분
    return ApiResponse(
        code="MEMBER_LIST_FETCHED",
        message="member 목록 조회 성공",
        #페이지 구조 생성
        data=PageOut[MemberOut](
            #DB 객체 -> API 응답용 모델로 변환
            #DB 모델 그대로 보내면 위험함: 불필요한 필드 포함, 보안 문제
            #그래서 Member -> MemberOut으로 변환
            items=[MemberOut.model_validate(item) for item in result["items"]],
            page=result["page"],
            size=result["size"],
            total=result["total"],
        ),
    )

#path: 경로, response_model: Swagger에서 보여줄 응답 예시 형태
#summary: Swagger에서 보여줄 간단한 API 설명
#description: Swagger에서 보여줄 상세한 API 설명
@router.get(
    path="",
    response_model=ApiResponse[MemberOut],
    summary="멤버 단건 조회",
    description="member ID에 해당하는 멤버의 상세 정보를 조회합니다.",
)
#DbSessionDep: DB 접속 정보
#Path: 경로 변수에게 설명을 추가할 수 있도록 하는 것
#Query: 쿼리 파라미터 변수에게 설명을 추가할 수 있도록 하는 것
#쿼리 파라미터: ex) /items?name=apple&page=2라고 한다면 name과 page가 쿼리 파라미터
async def get_member(
        service: MemberServiceDep,
        member_id: Annotated[UUID, Path(..., description="조회할 member의 id")],
        include_deleted: Annotated[bool, Query(description="soft delete된 데이터 포함 여부")] = False,
):
    #service = MemberService(session) new 하는 과정 다 없어짐
    member = await service.get(member_id, include_deleted=include_deleted)
    return ApiResponse.success(
        code="MEMBER_FETCHED",
        message="Member 조회 성공",
        data=member
    )

@router.post(
    path="",
    response_model=ApiResponse[MemberOut],
    status_code=status.HTTP_201_CREATED,
    summary="회원 생성",
    description="회원가입 기능입니다.",
)
async def create_member(
        data: MemberCreateIn,
        service: MemberServiceDep,
):
    created = await service.create(data)
    return ApiResponse.success(
        code="MEMBER_CREATED",
        message="회원가입 성공",
        data=MemberOut.model_validate(created)
    )

@router.patch(
    path="{member_id}",
    response_model=ApiResponse[MemberOut],
    summary="회원 정보 수정",
    description="회원 정보 수정 기능입니다."
)
async def update_member(
        #요청 JSON → (검증 + 파싱) → MemberUpdateIn 객체 → data로 들어옴
        #data는 검증 완료 된 Pydantic 객체
        data: MemberUpdateIn,
        #요청 들어오면 service = get_member_service() 자동 실행
        #->update_member(data, service, member_id) 이렇게 넣어줌
        #즉, MemberService 객체를 자동으로 만들어서 service에 넣어줘라는 뜻
        service: MemberServiceDep,
        #이건 URL에서 받는 UUID(Path에서 가져옴) 라고 알려주는 거
        member_id: Annotated[UUID, Path(description="수정할 member의 ID")],
):
    #DB 수정 → 수정된 객체 받음
    updated = await service.update(member_id, data)
    return ApiResponse.success(
        code="MEMBER_UPDATED",
        message="member 수정 성공",
        #밑에 과정 하는 이유
        #updated는 보통 SQLAlchemy 같은 ORM 객체인데 이걸 그대로 반영하면 Json 변환 안 되고, 내부 필드 노출 위험
        #그래서 밑에 과정을 함. 이 ORM 객체를 MemberOut 형태로 검증 + 변환해달라는 의미.
        data=MemberOut.model_validate(updated),
        #응답용 데이터로 변환 (필터링 + 검증)
    )
#model_dump()와 model_validated() 차이점
#model_dump(): Pydantic → dict(Json 형태)
#언제 할까?: DB에 넣을 때, PATCH 할 때 (exclude_unset=True), JSON 응답 만들 때
#model_validate(): 아무 데이터 → Pydantic 객체로 검증해서 만들어줌, ORM에서도 가능
#즉, model_dump()는 밖으로 꺼냄(요청), model_validated()는 안으로 넣음(응답)

@router.delete(
    path="/{member_id}",
    response_model=ApiResponse[None],
    summary="회원 삭제",
    description="기존 회원을 삭제합니다. hard가 true면 완전 삭제, false면 soft delete 처리합니다.",
)
async def delete_member(
        service: MemberServiceDep,
        member_id: Annotated[UUID, Path(description="삭제할 회원의 ID")],
        hard: Annotated[bool, Query(description="true면 hard delete, false면 soft delete", example=False)] = False,
):
    #실제 삭제는 여기서 일어남
    #router는 요청 받기만 하고, Service가 진짜 일함
    await service.delete(member_id, hard=hard)
    return ApiResponse.success(
        code="MEMBER_DELETED",
        message="member 삭제 성공",
        data=None
    )

@router.patch(
    path="/{member_id}/restore",
    response_model=ApiResponse[MemberOut],
    summary="회원 복구",
    description="soft delete 된 회원을 복구합니다."
)
async def restore_member(
        service: MemberServiceDep,
        member_id: Annotated[UUID, Path(description="복구할 member ID")],
):
    #밑 코드에서 일어나는 일
    #member 조회, 삭제된 상태인지 체크, is_deleted = False, deleted_at = None, commit, 최신 상태 반환
    #즉, 삭제 상태 -> 정상 상태로 되돌림
    restored = await service.restore(member_id)
    return ApiResponse.success(
        code="MEMBER_RESTORED",
        message="member 복구 성공",
        #ORM 객체 -> 응답용 Pydantic 모델로 변환
        #이 과정을 왜 하냐면...
        #restored는 SQLAlchemy 객체(DB 모델)이고, API 응답은 Pydantic 모델(Json용)이어서
        #쉽게 해서.. Member(DB용) -> MemberOut(응답용)
        data=MemberOut.model_validate(restored)
    )