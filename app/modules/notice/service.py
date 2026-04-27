from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.modules.notice.models import Notice
from app.modules.notice.repository import NoticeRepository
from app.modules.notice.schemas import NoticeCreateIn, NoticeUpdateIn


class NoticeService:
    def __init__(self, session: AsyncSession, repository: NoticeRepository):
        self.session = session
        self.repository = repository

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
