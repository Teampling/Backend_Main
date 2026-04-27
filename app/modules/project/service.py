import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError
from app.modules.member.repository import MemberRepository
from app.modules.project.models import Project, ProjectInvitation, ProjectMember
from app.modules.project.repository import ProjectRepository
from app.modules.project.schemas import ProjectCreateIn, ProjectUpdateIn
from app.shared.enums import InvitationStatus
from app.shared.utils.email import send_email


class ProjectService:
    def __init__(
            self,
            session: AsyncSession,
            repository: ProjectRepository,
            member_repository: MemberRepository
    ):
        self.session = session
        self.repository = repository
        self.member_repository = member_repository

    async def get(self, project_id: UUID, *, include_deleted: bool = False) -> Project:
        project = await self.repository.get_by_id(project_id, include_deleted=include_deleted)
        if not project:
            raise AppError.not_found(f"Project[{project_id}]")
        return project

    async def create(self, actor_member_id: UUID, data: ProjectCreateIn) -> Project:
        project = Project(
            **data.model_dump(),
            leader_id=actor_member_id
        )

        try:
            saved = await self.repository.save(project)
            await self.session.commit()
            await self.session.refresh(saved)
            return saved

        except IntegrityError:
            await self.session.rollback()
            raise AppError.bad_request(f"[{project.name}]은(는) 이미 존재하는 프로젝트입니다.")

    async def list(
        self,
        *,
        member_id: UUID | None = None,
        keyword: str | None = None,
        start_after: datetime | None = None,
        end_before: datetime | None = None,
        page: int = 1,
        size: int = 20,
        include_deleted: bool = False,
    ) -> dict[str, Any]:
        if page < 1:
            page = 1
        if size < 1:
            size = 1
        if size > 100:
            size = 100

        offset = (page - 1) * size

        items = await self.repository.list(
            member_id=member_id,
            keyword=keyword,
            start_after=start_after,
            end_before=end_before,
            offset=offset,
            limit=size,
            include_deleted=include_deleted,
        )
        total = await self.repository.count(
            member_id=member_id,
            keyword=keyword,
            start_after=start_after,
            end_before=end_before,
            include_deleted=include_deleted,
        )

        return {"items": items, "page": page, "size": size, "total": total}

    async def is_member(self, project_id: UUID, member_id: UUID) -> bool:
        return await self.repository.is_member(project_id, member_id)

    async def update(self, project_id: UUID, data: ProjectUpdateIn) -> Project:
        project = await self.get(project_id, include_deleted=False)
        if not project:
            raise AppError.not_found(f"Project[{project_id}]")

        patch = data.model_dump(
            exclude_unset=True,
        )

        for k, v in patch.items():
            setattr(project, k, v)

        try:
            updated = await self.repository.save(project)
            await self.session.commit()
            await self.session.refresh(updated)
            return updated

        except IntegrityError:
            await self.session.rollback()
            raise AppError.bad_request(f"[{project.name}] 수정 중 오류가 발생했습니다.")

    async def delete(self, project_id: UUID, *, hard: bool = False) -> None:
        project = await self.get(project_id, include_deleted=True)
        if not project:
            raise AppError.not_found(f"Project[{project_id}]")

        member_count = await self.repository.get_member_count(project_id)
        if member_count > 1:
            raise AppError.bad_request("나를 제외한 팀원이 남아있는 프로젝트는 삭제할 수 없습니다. 모든 팀원을 내보낸 후 삭제해주세요.")

        try:
            if hard:
                if not project.is_deleted:
                    raise AppError.bad_request("삭제되지 않은 프로젝트입니다.")
                await self.repository.hard_delete(project)
            else:
                if project.is_deleted:
                    raise AppError.bad_request("이미 삭제된 프로젝트입니다.")
                await self.repository.soft_delete(project)
            await self.session.commit()

        except Exception:
            await self.session.rollback()
            raise

    async def restore(self, project_id: UUID) -> Project:
        project = await self.repository.get_by_id(project_id, include_deleted=True)
        if not project:
            raise AppError.not_found(f"Project[{project_id}]")
        if not project.is_deleted:
            raise AppError.bad_request(f"Project[{project_id}]프로젝트는 삭제된 상태가 아닙니다.")

        try:
            project.is_deleted = False
            project.deleted_at = None

            restored = await self.repository.save(project)
            await self.session.commit()
            await self.session.refresh(restored)
            return restored

        except IntegrityError:
            await self.session.rollback()
            raise AppError.bad_request("프로젝트 복구 중 무결성 오류가 발생했습니다.")

        except Exception:
            await self.session.rollback()
            raise

    async def list_members(self, project_id: UUID) -> "list[dict[str, Any]]":
        """
        프로젝트 멤버 목록을 조회합니다.
        """
        project = await self.get(project_id)
        members_info = await self.repository.get_members_with_info(project_id)

        result = []
        # 리더 정보 추가
        leader = await self.member_repository.get_by_id(project.leader_id)
        if leader:
            result.append({
                "member": leader,
                "is_leader": True,
                "joined_at": project.created_at # 리더는 생성 시점부터 참여
            })

        # 나머지 멤버 정보 추가
        for member, joined_at in members_info:
            result.append({
                "member": member,
                "is_leader": False,
                "joined_at": joined_at
            })

        return result

    async def invite_member(self, project_id: UUID, member_id: UUID) -> ProjectInvitation:
        """
        특정 회원을 프로젝트에 초대합니다.
        """
        project = await self.get(project_id)
        invitee = await self.member_repository.get_by_id(member_id)
        if not invitee:
            raise AppError.not_found(f"회원[{member_id}]을 찾을 수 없습니다.")
        
        # 이미 멤버인지 확인
        if await self.repository.is_member(project_id, invitee.id):
            raise AppError.bad_request("이미 프로젝트의 멤버입니다.")

        # 초대장 생성
        token = secrets.token_urlsafe(32)
        invitation = ProjectInvitation(
            project_id=project_id,
            member_id=member_id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            status=InvitationStatus.PENDING
        )

        saved = await self.repository.save_invitation(invitation)
        
        # 이메일 발송
        invite_url = f"{settings.FRONTEND_URL}/project/invite/accept?token={token}"
        subject = f"[Teampling] {project.name} 프로젝트 초대"
        body = f"{invitee.username}님, {project.name} 프로젝트에 초대되었습니다.\n\n수락하시려면 아래 링크를 클릭하세요:\n{invite_url}"
        
        await send_email(subject, invitee.email, body)
        await self.session.commit()
        await self.session.refresh(saved)
        return saved

    async def accept_invitation(self, token: str, current_member_id: UUID) -> ProjectInvitation:
        """
        초대를 수락합니다.
        """
        invitation = await self.repository.get_invitation_by_token(token)
        if not invitation or invitation.status != InvitationStatus.PENDING:
            raise AppError.not_found("유효하지 않은 초대입니다.")
        
        if invitation.expires_at < datetime.now(timezone.utc):
            invitation.status = InvitationStatus.EXPIRED
            await self.session.commit()
            raise AppError.bad_request("만료된 초대입니다.")
        
        if invitation.member_id != current_member_id:
            raise AppError.forbidden("본인에게 발송된 초대가 아닙니다.")

        # 이미 멤버인지 다시 확인
        if not await self.repository.is_member(invitation.project_id, current_member_id):
            project_member = ProjectMember(
                project_id=invitation.project_id,
                member_id=current_member_id
            )
            self.session.add(project_member)

        invitation.status = InvitationStatus.ACCEPTED
        await self.session.commit()
        await self.session.refresh(invitation)
        return invitation

    async def decline_invitation(self, token: str, current_member_id: UUID) -> ProjectInvitation:
        """
        초대를 거절합니다.
        """
        invitation = await self.repository.get_invitation_by_token(token)
        if not invitation or invitation.status != InvitationStatus.PENDING:
            raise AppError.not_found("유효하지 않은 초대입니다.")
        
        if invitation.member_id != current_member_id:
            raise AppError.forbidden("본인에게 발송된 초대가 아닙니다.")

        invitation.status = InvitationStatus.DECLINED
        await self.session.commit()
        await self.session.refresh(invitation)
        return invitation

    async def remove_member(self, project_id: UUID, member_id: UUID) -> None:
        """
        멤버를 프로젝트에서 퇴출합니다.
        """
        project = await self.get(project_id)
        if member_id == project.leader_id:
            raise AppError.bad_request("리더는 자신을 퇴출할 수 없습니다.")
        
        await self.repository.delete_member(project_id, member_id)
        await self.session.commit()

    async def leave_project(self, project_id: UUID, member_id: UUID) -> None:
        """
        프로젝트에서 자진 탈퇴합니다.
        리더인 경우, 다른 팀원이 없으면 프로젝트를 삭제하며 탈퇴가 가능합니다.
        팀원이 남아있으면 리더는 탈퇴할 수 없습니다.
        """
        project = await self.get(project_id)
        
        if member_id == project.leader_id:
            member_count = await self.repository.get_member_count(project_id)
            if member_count >= 1:
                raise AppError.bad_request("팀원이 남아있는 상태에서는 리더가 탈퇴할 수 없습니다. 리더 권한을 위임하거나 모든 팀원을 내보낸 후 다시 시도해주세요.")
            
            # 혼자 남은 리더가 나가는 경우 프로젝트 삭제 처리
            await self.repository.soft_delete(project)
        else:
            await self.repository.delete_member(project_id, member_id)
            
        await self.session.commit()

    async def transfer_leader(
            self,
            project_id: UUID,
            actor_member_id: UUID,
            new_leader_member_id: UUID,
    ) -> Project:
        project = await self.get(project_id, include_deleted=False)
        if actor_member_id == new_leader_member_id:
            raise AppError.bad_request("본인에게 리더 권한을 위임할 수 없습니다.")

        new_leader = await self.member_repository.get_by_id(new_leader_member_id)
        if not new_leader:
            raise AppError.not_found(f"회원[{new_leader_member_id}]을 찾을 수 없습니다.")

        is_member = await self.repository.is_member(project_id, new_leader_member_id)
        if not is_member:
            raise AppError.bad_request("새 리더는 현재 프로젝트 멤버여야 합니다.")

        try:
            project.leader_id = new_leader_member_id
            updated = await self.repository.save(project)
            await self.repository.delete_member(project_id, new_leader_member_id)
            self.session.add(ProjectMember(project_id=project_id, member_id=actor_member_id))
            await self.session.commit()
            await self.session.refresh(updated)
            return updated

        except IntegrityError:
            await self.session.rollback()
            raise AppError.bad_request("리더 권한 위임 중 무결성 오류가 발생했습니다.")

        except Exception:
            await self.session.rollback()
            raise