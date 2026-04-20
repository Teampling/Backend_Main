from typing import Annotated
from uuid import UUID

from fastapi import Depends, Path

from app.core.database import DbSessionDep
from app.core.exceptions import AppError
from app.modules.member.dependencies import CurrentMemberDep
from app.modules.project.models import Project
from app.modules.project.repository import ProjectRepository
from app.modules.project.service import ProjectService


def get_project_service(session: DbSessionDep) -> ProjectService:
    repository = ProjectRepository(session)
    return ProjectService(session, repository)

ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]

async def get_project_participant(
    project_id: Annotated[UUID, Path(description="프로젝트 ID")],
    current_member: CurrentMemberDep,
    service: ProjectServiceDep,
) -> Project:
    """
    현재 사용자가 프로젝트의 참여자(리더 또는 멤버)인지 확인합니다.
    (삭제된 프로젝트도 권한 확인이 가능하도록 include_deleted=True 설정)
    """
    project = await service.get(project_id, include_deleted=True)
    if not await service.is_member(project_id, current_member.id):
        raise AppError.forbidden("해당 프로젝트의 참여자가 아닙니다.")
    return project

async def get_project_leader(
    project_id: Annotated[UUID, Path(description="프로젝트 ID")],
    current_member: CurrentMemberDep,
    service: ProjectServiceDep,
) -> Project:
    """
    현재 사용자가 프로젝트의 리더인지 확인합니다.
    (삭제된 프로젝트도 권한 확인이 가능하도록 include_deleted=True 설정)
    """
    project = await service.get(project_id, include_deleted=True)
    if project.leader_id != current_member.id:
        raise AppError.forbidden("해당 프로젝트의 리더 권한이 필요합니다.")
    return project

ProjectParticipantDep = Annotated[Project, Depends(get_project_participant)]
ProjectLeaderDep = Annotated[Project, Depends(get_project_leader)]