#resolver
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query, Depends, status

from app.core.database import DbSessionDep
from app.modules.member.models import Member
from app.modules.member.schemas import MemberCreateIn, MemberOut
from app.modules.member.service import MemberService
from app.shared.schemas import ApiResponse

#MemberService를 모든 Member api 함수들에게 의존성 주입을 하기 위한 과정
def get_member_service(session: DbSessionDep) -> MemberService:
    return MemberService(session)

MemberServiceDep = Annotated[MemberService, Depends(get_member_service)]

#prefix: 앞에 공통적으로 들어갈 경로명
#tags: Swagger에서 API를 분류할 때 사용하는 것
router = APIRouter(prefix="/members", tags=["Member"])

#path: 경로, response_model: Swagger에서 보여줄 응답 예시 형태
#summary: Swagger에서 보여줄 간단한 API 설명
#description: Swagger에서 보여줄 상세한 API 설명
@router.get(
    path="",
    response_model=ApiResponse[Member],
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