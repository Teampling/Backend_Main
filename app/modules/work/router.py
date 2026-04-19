from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Path
from starlette import status

from app.modules.member.dependencies import CurrentMemberDep
from app.modules.work.dependencies import WorkServiceDep
from app.modules.work.schemas import WorkOut, WorkCreateIn, WorkUpdateIn
from app.shared.schemas import ApiResponse, PageOut

router = APIRouter(prefix="/work", tags=["Work"])

@router.get(
    path="",
    response_model=ApiResponse[PageOut[WorkOut]],
    summary="작업 목록 조회",
    description="키워드, 페이지, 사이즈 조건으로 작업 목록을 조회합니다.",
)
async def list_works(
        service: WorkServiceDep,
        keyword: Annotated[str | None, Query(description="검색 키워드", example="팀플")] = None,
        page: Annotated[int, Query(ge=1, description="페이지 번호")] = 1,
        size: Annotated[int, Query(ge=1, le=100, description="페이지 크기")] = 50,
        include_deleted: Annotated[bool, Query(description="soft delete된 데이터 포함 여부")] = False,
):
    result = await service.list(
        keyword=keyword,
        page=page,
        size=size,
        include_deleted=include_deleted,
    )

    return ApiResponse(
        code="WORK_LIST_FETCHED",
        message="work 목록 조회 성공",
        data=PageOut[WorkOut](
            items=[WorkOut.model_validate(item) for item in result["items"]],
            page=result["page"],
            size=result["size"],
            total=result["total"],
        )
    )

@router.get(
    path="/{work_id}",
    response_model=ApiResponse[WorkOut],
    summary="작업 단건 조회",
    description="work ID에 해당하는 작업의 상세 정보를 조회합니다.",
)
async def get_project(
        service: WorkServiceDep,
        work_id: Annotated[UUID, Path(..., description="조회할 work의 id")],
        include_deleted: Annotated[bool, Query(description="soft delete된 데이터 포함 여부")] = False,
):
    work = await service.get(work_id, include_deleted=include_deleted)
    return ApiResponse.success(
        code="WORK_FETCHED",
        message="work 조회 성공",
        data=work
    )

@router.post(
    path="",
    response_model=ApiResponse[WorkOut],
    status_code=status.HTTP_201_CREATED,
    summary="작업 생성",
    description="작업 생성 기능입니다.",
)
async def create_work(
        current_member: CurrentMemberDep,
        data: WorkCreateIn,
        service: WorkServiceDep,
):
    created = await service.create(
        actor_member_id=current_member.id,
        data=data
    )
    return ApiResponse.success(
        code="WORK_CREATED",
        message="작업 생성 성공",
        data=WorkOut.model_validate(created)
    )

@router.patch(
    path="/{work_id}",
    response_model=ApiResponse[WorkOut],
    summary="작업 정보 수정",
    description="작업 정보 수정 기능입니다."
)
async def update_work(
        service: WorkServiceDep,
        current_member: CurrentMemberDep,
        work_id: Annotated[UUID, Path(description="수정할 work의 ID")],
        data: WorkUpdateIn,
):
    updated = await service.update(
        target_work_id=work_id,
        actor_member_id=current_member.id,
        data=data
    )
    return ApiResponse.success(
        code="WORK_UPDATED",
        message="work 수정 성공",
        data=WorkOut.model_validate(updated),
    )

@router.delete(
    path="/{work_id}",
    response_model=ApiResponse[None],
    summary="작업 삭제",
    description="기존 작업을 삭제합니다. hard가 true면 완전 삭제, false면 soft delete 처리합니다.",
)
async def delete_work(
        service: WorkServiceDep,
        current_member: CurrentMemberDep,
        work_id: Annotated[UUID, Path(description="삭제할 작업의 ID")],
        hard: Annotated[bool, Query(description="true면 hard delete, false면 soft delete, example=False")] = False,
):
    await service.delete(
        target_work_id=work_id,
        actor_member_id=current_member.id,
        hard=hard
    )
    return ApiResponse.success(
        code="WORK_DELETED",
        message="work 삭제 성공",
        data=None
    )

@router.patch(
    path="/{work_id}/restore",
    response_model=ApiResponse[WorkOut],
    summary="작업 복구",
    description="soft delete 된 작업을 복구합니다."
)
async def restore_work(
        service: WorkServiceDep,
        work_id: Annotated[UUID, Path(description="복구할 work의 ID")],
):
    restored = await service.restore(work_id)
    return ApiResponse.success(
        code="WORK_RESTORED",
        message="Work 복구 성공",
        data=WorkOut.model_validate(restored)
    )