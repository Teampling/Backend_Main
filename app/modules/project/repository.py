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
        result = await self.session.execute(query)
        return result.scalar()

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
        result = await self.session.execute(stmt)
        project_member = result.scalar()
        if project_member:
            await self.session.delete(project_member)

    async def save_invitation(self, invitation: ProjectInvitation) -> ProjectInvitation:
        self.session.add(invitation)
        await self.session.flush()
        return invitation

    async def get_invitation_by_token(self, token: str) -> ProjectInvitation | None:
        stmt = select(ProjectInvitation).where(ProjectInvitation.token == token)
        result = await self.session.execute(stmt)
        return result.scalar()

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
        result = await self.session.execute(project_stmt)
        if result.scalar():
            return True

        # 멤버인지 확인
        member_stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.member_id == member_id
        )
        result = await self.session.execute(member_stmt)
        if result.scalar():
            return True

        return False

    async def soft_delete(self, project: Project) -> Project:
        """
        프로젝트를 소프트 삭제하고 연관된 하위 리소스(공지, 할일 등)도 함께 소프트 삭제합니다.
        """
        from sqlalchemy import update, inspect
        
        now = datetime.now(timezone.utc)
        project.is_deleted = True
        project.deleted_at = now

        # 프로젝트와 연관된 모든 관계(Relationship)를 찾아서 자동으로 소프트 삭제 처리
        mapper = inspect(Project)
        for rel in mapper.relationships:
            # 연관된 모델 클래스 (Notice, Work, Resource 등)
            related_model = rel.mapper.class_
            
            # 모델에 is_deleted와 project_id 컬럼이 모두 있는지 확인 (하위 리소스인지 확인)
            if hasattr(related_model, "is_deleted") and hasattr(related_model, "project_id"):
                # 해당 프로젝트의 하위 데이터들을 일괄 업데이트
                stmt = (
                    update(related_model)
                    .where(related_model.project_id == project.id)
                    .where(related_model.is_deleted == False)
                    .values(is_deleted=True, deleted_at=now)
                )
                await self.session.execute(stmt)

        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def hard_delete(self, project: Project) -> None:
        await self.session.delete(project)
        await self.session.flush()