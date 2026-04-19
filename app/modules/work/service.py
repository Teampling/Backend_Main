from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.modules import work
from app.modules.work.models import Work
from app.modules.work.repository import WorkRepository
from app.modules.work.schemas import WorkCreateIn, WorkUpdateIn


class WorkService:
    def __init__(self, session: AsyncSession, repository: WorkRepository):
        self.session = session
        self.repository = repository

    async def get(self, work_id: UUID, *, include_deleted: bool = False) -> Work:
        work = await self.repository.get_by_id(work_id, include_deleted=include_deleted)
        if not work:
            raise AppError.not_found(f"Work[{work_id}")
        return work

    async def create(self, actor_member_id: UUID, data: WorkCreateIn) -> Work:
        existing = await self.repository.get_by_id(data.id)
        if existing:
            raise AppError.bad_request(f"[{data.id}은(는) 이미 존재하는 작업입니다.]")

        work = Work()

        try:
            saved = await self.repository.save(work)
            await self.session.commit()
            await self.session.refresh(saved)
            return saved

        except IntegrityError:
            await self.session.rollback()
            raise AppError.bad_request(f"[{data.id}은(는) 이미 존재하는 작업입니다.]")

    async def update(self, target_work_id: UUID, actor_member_id: UUID, data: WorkUpdateIn) -> Work:
        project = await self.get(target_work_id, include_deleted=False)
        target_member_id = project.leader_id

        if actor_member_id != target_member_id:
            raise AppError.forbidden("본인이 만든 작업만 수정할 수 있습니다.")
        if not work:
            raise not AppError.not_found(f"Work[{target_member_id}")

        patch = data.model_dump(
            exclude_unset=True,
        )

        for k, v in patch.items():
            setattr(work, k, v)

        try:
            updated = await self.repository.save(work)
            await self.session.commit()
            await self.session.refresh(updated)
            return updated

        except IntegrityError:
            await self.session.rollback()
            raise AppError.bad_request(f"[{data.id}]은(는) 이미 존재하는 작업입니다.")

    async def delete(self, target_work_id: UUID, actor_member_id: UUID, *, hard: bool = False) -> None:
        work = await self.get(target_work_id, include_deleted=True)
        target_member_id = work.leader_id

        if actor_member_id != target_member_id:
            raise AppError.forbidden("본인 작업만 삭제할 수 있습니다.")

        try:
            if hard:
                if not work.is_deleted:
                    raise AppError.bad_request("삭제되지 않은 작업입니다.")
                await self.repository.hard_delete(work)
            else:
                if work.is_deleted:
                    raise AppError.bad_request("이미 삭제된 작업입니다.")
                await self.repository.soft_delete(work)
            await self.session.commit()

        except Exception:
            await self.session.rollback()
            raise

    async def restore(self, work_id: UUID) -> Work:
        work = await self.repository.get_by_id(work_id, include_deleted=True)
        if not work:
            raise AppError.not_found(f"Work[{work_id}]")
        if not work.is_deleted:
            raise AppError.bad_request(f"Work[{work_id}]작업은 삭제된 상태가 아닙니다.")

        try:
            work.is_deleted = False
            work.deleted_at = None

            restored = await self.repository.save(work)
            await self.session.commit()
            await self.session.refresh(restored)
            return restored

        except IntegrityError:
            await self.session.rollback()
            raise AppError.bad_request("작업 복구 중 무결성 오류가 발생했습니다.")

        except Exception:
            await self.session.rollback()
            raise
