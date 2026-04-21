from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.modules.member.models import Member
from app.modules.project.models import Project, ProjectInvitation
from app.modules.project.models import ProjectMember
from app.shared.enums import InvitationStatus


class ProjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, project_id: UUID, *, include_deleted: bool = False) -> Project | None:
        query = select(Project).where(Project.id == project_id)
        if not include_deleted:
            query = query.where(Project.is_deleted == False)
        return await self.session.scalar(query)

    async def list(
            self,
            *,
            member_id: UUID | None = None,
            keyword: str | None = None,
            start_after: datetime | None = None,
            end_before: datetime | None = None,
            offset: int = 0,
            limit: int = 100,
            include_deleted: bool = False,
    ) -> list[Project]:
        stmt = select(Project)

        if member_id:
            stmt = stmt.join(ProjectMember, Project.id == ProjectMember.project_id, isouter=True).where(
                (Project.leader_id == member_id) | (ProjectMember.member_id == member_id)
            )

        if keyword:
            stmt = stmt.where(
                (Project.name.ilike(f"%{keyword}%")) |
                (Project.detail.ilike(f"%{keyword}%"))
            )

        if start_after:
            stmt = stmt.where(Project.start_date >= start_after)

        if end_before:
            stmt = stmt.where(Project.end_date <= end_before)

        if not include_deleted:
            stmt = stmt.where(Project.is_deleted == False)

        stmt = stmt.group_by(Project.id).order_by(Project.created_at.desc()).offset(offset).limit(limit)
        return (await self.session.scalars(stmt)).all()

    async def count(
            self,
            *,
            member_id: UUID | None = None,
            keyword: str | None = None,
            start_after: datetime | None = None,
            end_before: datetime | None = None,
            include_deleted: bool = False) -> int:
        stmt = select(func.count(func.distinct(Project.id))).select_from(Project)

        if member_id:
            stmt = stmt.join(ProjectMember, Project.id == ProjectMember.project_id, isouter=True).where(
                (Project.leader_id == member_id) | (ProjectMember.member_id == member_id)
            )

        if keyword:
            stmt = stmt.where(
                (Project.name.ilike(f"%{keyword}%")) |
                (Project.detail.ilike(f"%{keyword}%"))
            )

        if start_after:
            stmt = stmt.where(Project.start_date >= start_after)

        if end_before:
            stmt = stmt.where(Project.end_date <= end_before)

        if not include_deleted:
            stmt = stmt.where(Project.is_deleted == False)

        return int(await self.session.scalar(stmt) or 0)

    async def save(self, project: Project) -> Project:
        self.session.add(project)
        await self.session.flush()
        return project

    async def get_members_with_info(self, project_id: UUID) -> "list[tuple[Member, datetime]]":
        """
        프로젝트 멤버 정보와 합류일을 함께 조회합니다.
        """
        stmt = (
            select(Member, ProjectMember.joined_at)
            .join(ProjectMember, Member.id == ProjectMember.member_id)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.joined_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.all()

    async def delete_member(self, project_id: UUID, member_id: UUID) -> None:
        """
        프로젝트에서 멤버를 제거합니다.
        """
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.member_id == member_id
        )
        project_member = await self.session.scalar(stmt)
        if project_member:
            await self.session.delete(project_member)
            await self.session.flush()

    async def save_invitation(self, invitation: ProjectInvitation) -> ProjectInvitation:
        self.session.add(invitation)
        await self.session.flush()
        return invitation

    async def get_invitation_by_token(self, token: str) -> ProjectInvitation | None:
        stmt = select(ProjectInvitation).where(ProjectInvitation.token == token)
        return await self.session.scalar(stmt)

    async def get_invitations_by_project(self, project_id: UUID) -> "list[ProjectInvitation]":
        stmt = select(ProjectInvitation).where(
            ProjectInvitation.project_id == project_id,
            ProjectInvitation.status == InvitationStatus.PENDING
        )
        return (await self.session.scalars(stmt)).all()

    async def get_member_count(self, project_id: UUID) -> int:

        stmt = select(func.count()).select_from(ProjectMember).where(ProjectMember.project_id == project_id)
        return int(await self.session.scalar(stmt) or 0)

    async def is_member(self, project_id: UUID, member_id: UUID) -> bool:
        """
        사용자가 프로젝트의 리더이거나 멤버인지 확인합니다.
        """
        # 리더인지 확인
        project_stmt = select(Project).where(Project.id == project_id, Project.leader_id == member_id)
        if await self.session.scalar(project_stmt):
            return True

        # 멤버인지 확인
        member_stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.member_id == member_id
        )
        if await self.session.scalar(member_stmt):
            return True

        return False

    async def soft_delete(self, project: Project) -> Project:
        project.is_deleted = True
        project.deleted_at = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def hard_delete(self, project: Project) -> None:
        await self.session.delete(project)
        await self.session.flush()