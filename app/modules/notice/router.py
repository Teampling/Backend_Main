from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Path
from starlette import status

from app.modules.project.dependencies import ProjectParticipantDep, ProjectLeaderDep
from app.modules.notice.dependencies import NoticeServiceDep
from app.modules.notice.schemas import NoticeOut, NoticeCreateIn, NoticeUpdateIn
from app.shared.schemas import ApiResponse, PageOut

router = APIRouter(prefix="/project/{project_id}/notice", tags=["Notice"])

@router.get(
    path="",
    response_model=ApiResponse[PageOut[NoticeOut]],
    summary="프로젝트 공지 목록 조회",
    description="해당 프로젝트의 공지 목록을 조회합니다. 프로젝트 참여자만 가능합니다.",
)
async def list_project_notices(
        project: ProjectParticipantDep,
        service: NoticeServiceDep,
        keyword: Annotated[str | None, Query(description="검색 키워드(제목, 상세내용)")] = None,
        page: Annotated[int, Query(ge=1, description="페이지 번호")] = 1,
        size: Annotated[int, Query(ge=1, le=100, description="페이지 크기")] = 50,
        include_deleted: Annotated[bool, Query(description="soft delete된 데이터 포함 여부")] = False,
):
    result = await service.list(
        keyword=keyword,
        project_id=project.id,
        page=page,
        size=size,
        include_deleted=include_deleted,
    )

    return ApiResponse.success(
        code="PROJECT_NOTICE_LIST_FETCHED",
        message="프로젝트 공지 목록 조회 성공",
        data=PageOut[NoticeOut](
            items=[NoticeOut.model_validate(item) for item in result["items"]],
            page=result["page"],
            size=result["size"],
            total=result["total"],
        )
    )

@router.post(
    path="",
    response_model=ApiResponse[NoticeOut],
    status_code=status.HTTP_201_CREATED,
    summary="공지 생성",
    description="프로젝트 내에 공지를 생성합니다. 프로젝트 리더만 가능합니다.",
)
async def create_notice(
        project: ProjectLeaderDep,
        data: NoticeCreateIn,
        service: NoticeServiceDep,
):
    # 입력된 project_id가 경로의 project_id와 일치하는지 확인 (보안 강화)
    if data.project_id != project.id:
        from app.core.exceptions import AppError
        raise AppError.bad_request("경로의 프로젝트 ID와 요청 바디의 프로젝트 ID가 일치하지 않습니다.")

    created = await service.create(data=data)
    return ApiResponse.success(
        code="NOTICE_CREATED",
        message="공지 생성 성공",
        data=NoticeOut.model_validate(created)
    )

@router.get(
    path="/{notice_id}",
    response_model=ApiResponse[NoticeOut],
    summary="공지 단건 조회",
    description="프로젝트 내의 특정 공지를 조회합니다.",
)
async def get_project_notice(
        project: ProjectParticipantDep,
        service: NoticeServiceDep,
        notice_id: Annotated[UUID, Path(..., description="조회할 notice의 id")],
        include_deleted: Annotated[bool, Query(description="soft delete된 데이터 포함 여부")] = False,
):
    notice = await service.get(notice_id, include_deleted=include_deleted)
    
    # 해당 공지가 해당 프로젝트의 것인지 확인
    if notice.project_id != project.id:
        from app.core.exceptions import AppError
        raise AppError.not_found("해당 프로젝트에서 해당 공지를 찾을 수 없습니다.")
        
    return ApiResponse.success(
        code="NOTICE_FETCHED",
        message="공지 조회 성공",
        data=NoticeOut.model_validate(notice)
    )

@router.patch(
    path="/{notice_id}",
    response_model=ApiResponse[NoticeOut],
    summary="공지 정보 수정",
    description="기존 공지를 수정합니다. 프로젝트 리더만 가능합니다."
)
async def update_project_notice(
        project: ProjectLeaderDep,
        service: NoticeServiceDep,
        notice_id: Annotated[UUID, Path(description="수정할 notice의 ID")],
        data: NoticeUpdateIn,
):
    # 해당 공지가 해당 프로젝트의 것인지 확인
    notice = await service.get(notice_id)
    if notice.project_id != project.id:
        from app.core.exceptions import AppError
        raise AppError.not_found("해당 프로젝트에서 해당 공지를 찾을 수 없습니다.")

    updated = await service.update(
        target_notice_id=notice_id,
        data=data
    )
    return ApiResponse.success(
        code="NOTICE_UPDATED",
        message="공지 수정 성공",
        data=NoticeOut.model_validate(updated),
    )

@router.delete(
    path="/{notice_id}",
    response_model=ApiResponse[None],
    summary="공지 삭제",
    description="기존 공지를 삭제합니다. 프로젝트 리더만 가능합니다.",
)
async def delete_project_notice(
        project: ProjectLeaderDep,
        service: NoticeServiceDep,
        notice_id: Annotated[UUID, Path(description="삭제할 공지의 ID")],
        hard: Annotated[bool, Query(description="true면 hard delete, false면 soft delete")] = False,
):
    # 해당 공지가 해당 프로젝트의 것인지 확인
    notice = await service.get(notice_id, include_deleted=True)
    if notice.project_id != project.id:
        from app.core.exceptions import AppError
        raise AppError.not_found("해당 프로젝트에서 해당 공지를 찾을 수 없습니다.")

    await service.delete(
        target_notice_id=notice_id,
        hard=hard
    )
    return ApiResponse.success(
        code="NOTICE_DELETED",
        message="공지 삭제 성공",
        data=None
    )

@router.patch(
    path="/{notice_id}/restore",
    response_model=ApiResponse[NoticeOut],
    summary="공지 복구",
    description="soft delete 된 공지를 복구합니다. 프로젝트 리더만 가능합니다."
)
async def restore_project_notice(
        project: ProjectLeaderDep,
        service: NoticeServiceDep,
        notice_id: Annotated[UUID, Path(description="복구할 notice의 ID")],
):
    # 해당 공지가 해당 프로젝트의 것인지 확인
    notice = await service.get(notice_id, include_deleted=True)
    if notice.project_id != project.id:
        from app.core.exceptions import AppError
        raise AppError.not_found("해당 프로젝트에서 해당 공지를 찾을 수 없습니다.")

    restored = await service.restore(notice_id)
    return ApiResponse.success(
        code="NOTICE_RESTORED",
        message="공지 복구 성공",
        data=NoticeOut.model_validate(restored)
    )
