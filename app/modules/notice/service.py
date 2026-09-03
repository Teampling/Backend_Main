from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.modules.notice.models import Notice
from app.modules.notice.repository import NoticeRepository
from app.modules.notice.schemas import NoticeCreateIn, NoticeUpdateIn
from app.modules.notification.events import NotificationEvents
from app.modules.project.repository import ProjectRepository


class NoticeService:
    def __init__(self, session: AsyncSession, repository: NoticeRepository, project_repository: ProjectRepository):
        self.session = session
        self.repository = repository
        self.project_repository = project_repository

    async def _get_project_member_ids(self, project_id: UUID) -> list[UUID]:
        """공지 알림을 팬아웃할 대상(리더 + 멤버 전원)의 id 목록."""
        project = await self.project_repository.get_by_id(project_id, include_deleted=True)
        if not project:
            return []

        members_info = await self.project_repository.get_members_with_info(project_id)
        member_ids = [member.id for member, _ in members_info]
        member_ids.append(project.leader_id)
        return member_ids

    async def get(self, notice_id: UUID, *, include_deleted: bool = False) -> Notice:
        notice = await self.repository.get_by_id(notice_id, include_deleted=include_deleted)
        if not notice:
            raise AppError.not_found("해당 공지를 찾을 수 없습니다.")
        return notice

    async def list(
            self,
            *,
            keyword: str | None = None,
            project_id: UUID | None = None,
            page: int = 1,
            size: int = 50,
            include_deleted: bool = False,
    ) -> dict:
        offset = (page - 1) * size
        items = await self.repository.list(
            keyword=keyword,
            project_id=project_id,
            offset=offset,
            limit=size,
            include_deleted=include_deleted
        )
        total = await self.repository.count(
            keyword=keyword,
            project_id=project_id,
            include_deleted=include_deleted
        )

        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
        }

    async def create(self, data: NoticeCreateIn) -> Notice:
        notice = Notice(
            project_id=data.project_id,
            title=data.title,
            detail=data.detail,
        )
        try:
            saved = await self.repository.save(notice)

            # 알림 이벤트를 아웃박스에 기록 (같은 트랜잭션 -> 공지 저장과 원자적으로 커밋된다).
            recipient_ids = await self._get_project_member_ids(data.project_id)
            if recipient_ids:
                NotificationEvents.notice_created(
                    self.session,
                    notice_id=saved.id,
                    title=saved.title,
                    detail=saved.detail,
                    recipient_ids=recipient_ids,
                )

            await self.session.commit()
            await self.session.refresh(saved)
            return saved
        except Exception:
            await self.session.rollback()
            raise

    async def update(self, target_notice_id: UUID, data: NoticeUpdateIn) -> Notice:
        notice = await self.get(target_notice_id)

        if data.title is not None:
            notice.title = data.title
        if data.detail is not None:
            notice.detail = data.detail

        try:
            updated = await self.repository.save(notice)
            await self.session.commit()
            await self.session.refresh(updated)
            return updated
        except Exception:
            await self.session.rollback()
            raise

    async def delete(self, target_notice_id: UUID, *, hard: bool = False) -> None:
        notice = await self.get(target_notice_id, include_deleted=True)

        try:
            if hard:
                await self.repository.hard_delete(notice)
            else:
                if notice.is_deleted:
                    raise AppError.bad_request("이미 삭제된 공지입니다.")
                await self.repository.soft_delete(notice)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def restore(self, target_notice_id: UUID) -> Notice:
        notice = await self.get(target_notice_id, include_deleted=True)

        if not notice.is_deleted:
            raise AppError.bad_request("삭제되지 않은 공지는 복구할 수 없습니다.")

        notice.is_deleted = False
        notice.deleted_at = None

        try:
            restored = await self.repository.save(notice)
            await self.session.commit()
            await self.session.refresh(restored)
            return restored
        except Exception:
            await self.session.rollback()
            raise
