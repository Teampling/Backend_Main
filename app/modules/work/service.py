from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.modules.work.models import Work
from app.modules.work.repository import WorkRepository
from app.modules.work.schemas import WorkCreateIn, WorkUpdateIn
from app.modules.notification.events import NotificationEvents
from app.shared.enums import WorkState


class WorkService:
    def __init__(self, session: AsyncSession, repository: WorkRepository):
        self.session = session
        self.repository = repository

    async def get(self, work_id: UUID, *, include_deleted: bool = False) -> Work:
        work = await self.repository.get_by_id(work_id, include_deleted=include_deleted)
        if not work:
            raise AppError.not_found(f"Work[{work_id}]")
        return work

    async def list(
            self,
            *,
            keyword: str | None = None,
            author_id: UUID | None = None,
            project_id: UUID | None = None,
            states: list[WorkState] | None = None,
            page: int = 1,
            size: int = 50,
            include_deleted: bool = False,
    ) -> dict[str, Any]:
        offset = (page - 1) * size
        items = await self.repository.list(
            keyword=keyword,
            author_id=author_id,
            project_id=project_id,
            states=states,
            offset=offset,
            limit=size,
            include_deleted=include_deleted,
        )
        total = await self.repository.count(
            keyword=keyword,
            author_id=author_id,
            project_id=project_id,
            states=states,
            include_deleted=include_deleted,
        )

        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
        }

    async def get_stats(self, project_id: UUID) -> dict[str, int]:
        return await self.repository.get_stats_by_project(project_id)

    async def create(self, actor_member_id: UUID, data: WorkCreateIn) -> Work:
        dump = data.model_dump()
        assignee_ids = dump.pop("assignee_ids", [])
        work = Work(**dump, author_id=actor_member_id)

        try:
            saved = await self.repository.save(work)
            work_id = saved.id
            project_id = saved.project_id
            title = saved.title
            await self.repository.set_assignees(work_id, assignee_ids)
            NotificationEvents.work_assigned(
                self.session,
                work_id=work_id,
                project_id=project_id,
                title=title,
                recipient_ids=assignee_ids,
            )
            await self.session.commit()
            return await self.get(work_id)

        except IntegrityError as e:
            await self.session.rollback()
            raise AppError.bad_request("작업 생성 중 오류가 발생했습니다.") from e

    async def update(self, target_work_id: UUID, actor_member_id: UUID, data: WorkUpdateIn) -> Work:
        work = await self.get(target_work_id, include_deleted=False)

        if actor_member_id != work.author_id:
            raise AppError.forbidden("본인이 만든 작업만 수정할 수 있습니다.")

        patch = data.model_dump(exclude_unset=True)
        new_assignee_ids = patch.pop("assignee_ids", None)
        state_provided = "state" in patch
        prev_state = work.state

        for k, v in patch.items():
            setattr(work, k, v)

        try:
            updated = await self.repository.save(work)

            # 담당자 교체 + 새로 추가된 담당자에게 work_assigned
            if new_assignee_ids is not None:
                prev_assignees = set(await self.repository.get_assignee_ids(target_work_id))
                await self.repository.set_assignees(target_work_id, new_assignee_ids)
                newly_added = [m for m in dict.fromkeys(new_assignee_ids) if m not in prev_assignees]
                NotificationEvents.work_assigned(
                    self.session,
                    work_id=updated.id,
                    project_id=updated.project_id,
                    title=updated.title,
                    recipient_ids=newly_added,
                )

            # 상태 변경 시 담당자 + 작성자에게 work_status_changed
            if state_provided and updated.state != prev_state:
                if new_assignee_ids is not None:
                    assignee_ids = list(dict.fromkeys(new_assignee_ids))
                else:
                    assignee_ids = await self.repository.get_assignee_ids(target_work_id)
                recipients = list(dict.fromkeys([*assignee_ids, updated.author_id]))
                NotificationEvents.work_status_changed(
                    self.session,
                    work_id=updated.id,
                    project_id=updated.project_id,
                    title=updated.title,
                    recipient_ids=recipients,
                )

            await self.session.commit()
            return await self.get(target_work_id)

        except IntegrityError as e:
            await self.session.rollback()
            raise AppError.bad_request("작업 수정 중 오류가 발생했습니다.") from e

    async def delete(self, target_work_id: UUID, actor_member_id: UUID, *, hard: bool = False) -> None:
        work = await self.get(target_work_id, include_deleted=True)

        if actor_member_id != work.author_id:
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

    async def restore(self, work_id: UUID, actor_member_id: UUID) -> Work:
        work = await self.repository.get_by_id(work_id, include_deleted=True)
        if not work:
            raise AppError.not_found(f"Work[{work_id}]")
        
        if actor_member_id != work.author_id:
             raise AppError.forbidden("본인 작업만 복구할 수 있습니다.")
             
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
