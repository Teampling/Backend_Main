from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Path
from starlette import status

from app.modules.member.dependencies import CurrentMemberDep
from app.modules.project.dependencies import ProjectParticipantDep
from app.modules.work.dependencies import WorkServiceDep
from app.modules.work.schemas import WorkOut, WorkCreateIn, WorkUpdateIn
from app.shared.enums import WorkState
from app.shared.schemas import ApiResponse, PageOut

# 전역 워크 라우터 (예: /work/me)
work_router = APIRouter(prefix="/work", tags=["Work"])

# 프로젝트 하위 워크 라우터 (예: /project/{project_id}/work)
project_work_router = APIRouter(prefix="/project/{project_id}/work", tags=["Project Work"])

# --- 전역 기능 ---

@work_router.get(
    path="/me",
    response_model=ApiResponse[PageOut[WorkOut]],
    summary="내 작업 목록 조회",
    description="내가 작성한 모든 작업 목록을 조회합니다.",
)
async def list_my_works(
        current_member: CurrentMemberDep,
        service: WorkServiceDep,
        keyword: Annotated[str | None, Query(description="검색 키워드(제목, 상세내용)")] = None,
        project_id: Annotated[UUID | None, Query(description="프로젝트 ID")] = None,
        states: Annotated[list[WorkState] | None, Query(description="상태 필터")] = None,
        page: Annotated[int, Query(ge=1, description="페이지 번호")] = 1,
        size: Annotated[int, Query(ge=1, le=100, description="페이지 크기")] = 50,
):
    result = await service.list(
        keyword=keyword,
        author_id=current_member.id,
        project_id=project_id,
        states=states,
        page=page,
        size=size,
    )

    return ApiResponse.success(
        code="MY_WORK_LIST_FETCHED",
        message="내 작업 목록 조회 성공",
        data=PageOut[WorkOut](
            items=[WorkOut.model_validate(item) for item in result["items"]],
            page=result["page"],
            size=result["size"],
            total=result["total"],
        )
    )

# --- 프로젝트 종속 기능 (ProjectParticipantDep 적용) ---

@project_work_router.get(
    path="",
    response_model=ApiResponse[PageOut[WorkOut]],
    summary="프로젝트 내 작업 목록 조회",
    description="해당 프로젝트의 작업 목록을 조회합니다. 프로젝트 참여자만 가능합니다.",
)
async def list_project_works(
        project: ProjectParticipantDep,
        service: WorkServiceDep,
        keyword: Annotated[str | None, Query(description="검색 키워드(제목, 상세내용)")] = None,
        author_id: Annotated[UUID | None, Query(description="작성자 ID")] = None,
        states: Annotated[list[WorkState] | None, Query(description="상태 필터")] = None,
        page: Annotated[int, Query(ge=1, description="페이지 번호")] = 1,
        size: Annotated[int, Query(ge=1, le=100, description="페이지 크기")] = 50,
        include_deleted: Annotated[bool, Query(description="soft delete된 데이터 포함 여부")] = False,
):
    result = await service.list(
        keyword=keyword,
        author_id=author_id,
        project_id=project.id,
        states=states,
        page=page,
        size=size,
        include_deleted=include_deleted,
    )

    return ApiResponse.success(
        code="PROJECT_WORK_LIST_FETCHED",
        message="프로젝트 작업 목록 조회 성공",
        data=PageOut[WorkOut](
            items=[WorkOut.model_validate(item) for item in result["items"]],
            page=result["page"],
            size=result["size"],
            total=result["total"],
        )
    )

@project_work_router.get(
    path="/stats",
    response_model=ApiResponse[dict[str, int]],
    summary="프로젝트 작업 통계",
    description="특정 프로젝트의 작업 상태별 개수를 조회합니다. 프로젝트 참여자만 가능합니다.",
)
async def get_project_work_stats(
        project: ProjectParticipantDep,
        service: WorkServiceDep,
):
    stats = await service.get_stats(project.id)
    return ApiResponse.success(
        code="PROJECT_WORK_STATS_FETCHED",
        message="작업 통계 조회 성공",
        data=stats
    )

@project_work_router.post(
    path="",
    response_model=ApiResponse[WorkOut],
    status_code=status.HTTP_201_CREATED,
    summary="작업 생성",
    description="프로젝트 내에 작업을 생성합니다. 프로젝트 참여자만 가능합니다.",
)
async def create_work(
        project: ProjectParticipantDep,
        current_member: CurrentMemberDep,
        data: WorkCreateIn,
        service: WorkServiceDep,
):
    # 입력된 project_id가 경로의 project_id와 일치하는지 확인 (보안 강화)
    if data.project_id != project.id:
        from app.core.exceptions import AppError
        raise AppError.bad_request("경로의 프로젝트 ID와 요청 바디의 프로젝트 ID가 일치하지 않습니다.")

    created = await service.create(
        actor_member_id=current_member.id,
        data=data
    )
    return ApiResponse.success(
        code="WORK_CREATED",
        message="작업 생성 성공",
        data=WorkOut.model_validate(created)
    )

@project_work_router.get(
    path="/{work_id}",
    response_model=ApiResponse[WorkOut],
    summary="작업 단건 조회",
    description="프로젝트 내의 특정 작업을 조회합니다.",
)
async def get_project_work(
        project: ProjectParticipantDep,
        service: WorkServiceDep,
        work_id: Annotated[UUID, Path(..., description="조회할 work의 id")],
        include_deleted: Annotated[bool, Query(description="soft delete된 데이터 포함 여부")] = False,
):
    work = await service.get(work_id, include_deleted=include_deleted)
    
    # 해당 작업이 해당 프로젝트의 것인지 확인
    if work.project_id != project.id:
        from app.core.exceptions import AppError
        raise AppError.not_found("해당 프로젝트에서 해당 작업을 찾을 수 없습니다.")
        
    return ApiResponse.success(
        code="WORK_FETCHED",
        message="work 조회 성공",
        data=WorkOut.model_validate(work)
    )

@project_work_router.patch(
    path="/{work_id}",
    response_model=ApiResponse[WorkOut],
    summary="작업 정보 수정",
    description="기존 작업을 수정합니다. 본인 작업만 가능합니다."
)
async def update_project_work(
        project: ProjectParticipantDep,
        service: WorkServiceDep,
        current_member: CurrentMemberDep,
        work_id: Annotated[UUID, Path(description="수정할 work의 ID")],
        data: WorkUpdateIn,
):
    # 서비스 레이어에서 본인 확인 로직이 이미 포함되어 있음
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

@project_work_router.delete(
    path="/{work_id}",
    response_model=ApiResponse[None],
    summary="작업 삭제",
    description="기존 작업을 삭제합니다. 본인 작업만 가능합니다.",
)
async def delete_project_work(
        project: ProjectParticipantDep,
        service: WorkServiceDep,
        current_member: CurrentMemberDep,
        work_id: Annotated[UUID, Path(description="삭제할 작업의 ID")],
        hard: Annotated[bool, Query(description="true면 hard delete, false면 soft delete")] = False,
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

@project_work_router.patch(
    path="/{work_id}/restore",
    response_model=ApiResponse[WorkOut],
    summary="작업 복구",
    description="soft delete 된 작업을 복구합니다. 본인 작업만 가능합니다."
)
async def restore_project_work(
        project: ProjectParticipantDep,
        service: WorkServiceDep,
        current_member: CurrentMemberDep,
        work_id: Annotated[UUID, Path(description="복구할 work의 ID")],
):
    restored = await service.restore(work_id, actor_member_id=current_member.id)
    return ApiResponse.success(
        code="WORK_RESTORED",
        message="Work 복구 성공",
        data=WorkOut.model_validate(restored)
    )
