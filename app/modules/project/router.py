from uuid import UUID
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Path, Query, Depends, status

from app.modules.member.dependencies import CurrentMemberDep
from app.modules.project.dependencies import ProjectServiceDep
from app.modules.project.schemas import ProjectOut, ProjectCreateIn, ProjectUpdateIn
from app.shared.schemas import ApiResponse, PageOut

router = APIRouter(prefix="/project", tags=["Project"])

@router.get(
    path="",
    response_model=ApiResponse[PageOut[ProjectOut]],
    summary="프로젝트 목록 조회",
    description="키워드, 날짜 범위, 페이지, 사이즈 조건으로 프로젝트 목록을 조회합니다.",
)
async def list_projects(
        service: ProjectServiceDep,
        keyword: Annotated[str | None, Query(description="검색 키워드 (이름, 상세설명)", example="팀플")] = None,
        start_after: Annotated[datetime | None, Query(description="조회 시작일 (이 날짜 이후 시작된 프로젝트)")] = None,
        end_before: Annotated[datetime | None, Query(description="조회 종료일 (이 날짜 이전 종료된 프로젝트)")] = None,
        page: Annotated[int, Query(ge=1, description="페이지 번호")] = 1,
        size: Annotated[int, Query(ge=1, le=100, description="페이지 크기")] = 50,
        include_deleted: Annotated[bool, Query(description="soft delete된 데이터 포함 여부")] = False,
):
    result = await service.list(
        keyword=keyword,
        start_after=start_after,
        end_before=end_before,
        page=page,
        size=size,
        include_deleted=include_deleted,
    )

    return ApiResponse.success(
        code="PROJECT_LIST_FETCHED",
        message="프로젝트 목록 조회 성공",
        data=PageOut[ProjectOut](
            items=[ProjectOut.model_validate(item) for item in result["items"]],
            page=result["page"],
            size=result["size"],
            total=result["total"],
        )
    )

@router.get(
    path="/{project_id}",
    response_model=ApiResponse[ProjectOut],
    summary="프로젝트 단건 조회",
    description="project ID에 해당하는 프로젝트의 상세 정보를 조회합니다.",
)
async def get_project(
        service: ProjectServiceDep,
        project_id: Annotated[UUID, Path(..., description="조회할 project의 id")],
        include_deleted: Annotated[bool, Query(description="soft delete된 데이터 포함 여부")] = False,
):
    project = await service.get(project_id, include_deleted=include_deleted)
    return ApiResponse.success(
        code="PROJECT_FETCHED",
        message="Project 조회 성공",
        data=project
    )

@router.post(
    path="",
    response_model=ApiResponse[ProjectOut],
    status_code=status.HTTP_201_CREATED,
    summary="프로젝트 생성",
    description="프로젝트 생성 기능입니다.",
)
async def create_project(
        current_member: CurrentMemberDep,
        data: ProjectCreateIn,
        service: ProjectServiceDep,
):
    created = await service.create(
        actor_member_id=current_member.id,
        data=data
    )
    return ApiResponse.success(
        code="PROJECT_CREATED",
        message="프로젝트 생성 성공",
        data=ProjectOut.model_validate(created)
    )

@router.patch(
    path="/{project_id}",
    response_model=ApiResponse[ProjectOut],
    summary="프로젝트 정보 수정",
    description="프로젝트 정보 수정 기능입니다."
)
async def update_project(
        service: ProjectServiceDep,
        current_member: CurrentMemberDep,
        project_id: Annotated[UUID, Path(description="수정할 project의 ID")],
        data: ProjectUpdateIn,
):
    updated = await service.update(
        target_project_id=project_id,
        actor_member_id=current_member.id,
        data=data
    )
    return ApiResponse.success(
        code="PROJECT_UPDATED",
        message="project 수정 성공",
        data=ProjectOut.model_validate(updated),
    )

@router.delete(
    path="/{project_id}",
    response_model=ApiResponse[None],
    summary="프로젝트 삭제",
    description="기존 프로젝트를 삭제합니다. hard가 true면 완전 삭제, false면 soft delete 처리합니다.",
)
async def delete_project(
        service: ProjectServiceDep,
        current_member: CurrentMemberDep,
        project_id: Annotated[UUID, Path(description="삭제할 프로젝트의 ID")],
        hard: Annotated[bool, Query(description="true면 hard delete, false면 soft delete, example=False")] = False,
):
    await service.delete(
        target_project_id=project_id,
        actor_member_id=current_member.id,
        hard=hard
    )
    return ApiResponse.success(
        code="PROJECT_DELETED",
        message="프로젝트 삭제 성공",
        data=None
    )

@router.post(
    path="/{project_id}/restore",
    response_model=ApiResponse[ProjectOut],
    summary="프로젝트 복구",
    description="삭제된 프로젝트를 복구합니다.",
)
async def restore_project(
        service: ProjectServiceDep,
        project_id: Annotated[UUID, Path(description="복구할 프로젝트의 ID")],
):
    restored = await service.restore(project_id)
    return ApiResponse.success(
        code="PROJECT_RESTORED",
        message="프로젝트 복구 성공",
        data=ProjectOut.model_validate(restored)
    )