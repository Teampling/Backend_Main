from uuid import UUID
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Path, Query, Depends, status

from app.modules.member.dependencies import CurrentMemberDep, OptionalMemberDep
from app.modules.project.dependencies import ProjectServiceDep, ProjectLeaderDep, ProjectParticipantDep
from app.modules.project.schemas import (
    ProjectOut, ProjectCreateIn, ProjectUpdateIn,
    ProjectMemberOut, ProjectInviteIn, ProjectInvitationOut
)
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
        current_member: OptionalMemberDep,
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

    items = []
    for item in result["items"]:
        p = ProjectOut.model_validate(item)
        if current_member:
            p.is_leader = (item.leader_id == current_member.id)
            p.is_member = await service.is_member(item.id, current_member.id)
        items.append(p)

    return ApiResponse.success(
        code="PROJECT_LIST_FETCHED",
        message="프로젝트 목록 조회 성공",
        data=PageOut[ProjectOut](
            items=items,
            page=result["page"],
            size=result["size"],
            total=result["total"],
        )
    )

@router.get(
    path="/me",
    response_model=ApiResponse[PageOut[ProjectOut]],
    summary="내 프로젝트 목록 조회",
    description="로그인한 사용자가 참여 중이거나 리더인 프로젝트 목록을 조회합니다.",
)
async def list_my_projects(
        current_member: CurrentMemberDep,
        service: ProjectServiceDep,
        page: Annotated[int, Query(ge=1, description="페이지 번호")] = 1,
        size: Annotated[int, Query(ge=1, le=100, description="페이지 크기")] = 50,
):
    result = await service.list(
        member_id=current_member.id,
        page=page,
        size=size,
    )

    items = []
    for item in result["items"]:
        p = ProjectOut.model_validate(item)
        p.is_leader = (item.leader_id == current_member.id)
        p.is_member = True # 내 프로젝트 목록이므로 항상 True
        items.append(p)

    return ApiResponse.success(
        code="MY_PROJECT_LIST_FETCHED",
        message="내 프로젝트 목록 조회 성공",
        data=PageOut[ProjectOut](
            items=items,
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
        current_member: OptionalMemberDep,
        project_id: Annotated[UUID, Path(..., description="조회할 project의 id")],
        include_deleted: Annotated[bool, Query(description="soft delete된 데이터 포함 여부")] = False,
):
    project = await service.get(project_id, include_deleted=include_deleted)
    data = ProjectOut.model_validate(project)
    if current_member:
        data.is_leader = (project.leader_id == current_member.id)
        data.is_member = await service.is_member(project.id, current_member.id)
        
    return ApiResponse.success(
        code="PROJECT_FETCHED",
        message="Project 조회 성공",
        data=data
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
        project: ProjectLeaderDep,
        data: ProjectUpdateIn,
):
    updated = await service.update(
        project_id=project.id,
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
        project: ProjectLeaderDep,
        hard: Annotated[bool, Query(description="true면 hard delete, false면 soft delete, example=False")] = False,
):
    await service.delete(
        project_id=project.id,
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
        project: ProjectLeaderDep,
):
    restored = await service.restore(project.id)
    return ApiResponse.success(
        code="PROJECT_RESTORED",
        message="프로젝트 복구 성공",
        data=ProjectOut.model_validate(restored)
    )

@router.get(
    path="/{project_id}/members",
    response_model=ApiResponse[list[ProjectMemberOut]],
    summary="프로젝트 멤버 목록 조회",
    description="해당 프로젝트에 참여 중인 모든 멤버 목록을 조회합니다.",
)
async def list_project_members(
        service: ProjectServiceDep,
        project: ProjectParticipantDep,
):
    members = await service.list_members(project.id)
    return ApiResponse.success(
        code="PROJECT_MEMBERS_FETCHED",
        message="프로젝트 멤버 목록 조회 성공",
        data=[ProjectMemberOut(**m) for m in members]
    )

@router.post(
    path="/{project_id}/invite",
    response_model=ApiResponse[ProjectInvitationOut],
    summary="프로젝트 멤버 초대",
    description="이메일을 통해 프로젝트 멤버를 초대합니다.",
)
async def invite_project_member(
        service: ProjectServiceDep,
        project: ProjectLeaderDep,
        data: ProjectInviteIn,
):
    invitation = await service.invite_member(project.id, data.member_id)
    return ApiResponse.success(
        code="PROJECT_MEMBER_INVITED",
        message="초대장을 발송했습니다.",
        data=ProjectInvitationOut.model_validate(invitation)
    )

@router.post(
    path="/invite/accept",
    response_model=ApiResponse[ProjectInvitationOut],
    summary="프로젝트 초대 수락",
    description="전송된 토큰을 사용하여 프로젝트 초대를 수락합니다.",
)
async def accept_project_invitation(
        service: ProjectServiceDep,
        current_member: CurrentMemberDep,
        token: Annotated[str, Query(..., description="초대 토큰")],
):
    invitation = await service.accept_invitation(token, current_member.id)
    return ApiResponse.success(
        code="PROJECT_INVITATION_ACCEPTED",
        message="프로젝트 초대를 수락했습니다.",
        data=ProjectInvitationOut.model_validate(invitation)
    )

@router.post(
    path="/invite/decline",
    response_model=ApiResponse[ProjectInvitationOut],
    summary="프로젝트 초대 거절",
    description="전송된 토큰을 사용하여 프로젝트 초대를 거절합니다.",
)
async def decline_project_invitation(
        service: ProjectServiceDep,
        current_member: CurrentMemberDep,
        token: Annotated[str, Query(..., description="초대 토큰")],
):
    invitation = await service.decline_invitation(token, current_member.id)
    return ApiResponse.success(
        code="PROJECT_INVITATION_DECLINED",
        message="프로젝트 초대를 거절했습니다.",
        data=ProjectInvitationOut.model_validate(invitation)
    )

@router.delete(
    path="/{project_id}/members/{member_id}",
    response_model=ApiResponse[None],
    summary="프로젝트 멤버 퇴출",
    description="프로젝트에서 특정 멤버를 퇴출시킵니다. 리더만 가능합니다.",
)
async def remove_project_member(
        service: ProjectServiceDep,
        project: ProjectLeaderDep,
        member_id: Annotated[UUID, Path(..., description="퇴출할 멤버의 ID")],
):
    await service.remove_member(project.id, member_id)
    return ApiResponse.success(
        code="PROJECT_MEMBER_REMOVED",
        message="멤버를 퇴출시켰습니다.",
        data=None
    )

@router.delete(
    path="/{project_id}/leave",
    response_model=ApiResponse[None],
    summary="프로젝트 자진 탈퇴",
    description="참여 중인 프로젝트에서 자진 탈퇴합니다.",
)
async def leave_project(
        service: ProjectServiceDep,
        current_member: CurrentMemberDep,
        project_id: Annotated[UUID, Path(..., description="탈퇴할 프로젝트의 ID")],
):
    await service.leave_project(project_id, current_member.id)
    return ApiResponse.success(
        code="PROJECT_LEFT",
        message="프로젝트에서 탈퇴했습니다.",
        data=None
    )