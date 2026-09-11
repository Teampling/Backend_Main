from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notification.repository import OutboxEventRepository
from app.shared.enums import NotificationEventType, NotificationTargetType


class NotificationEvents:

    # ---------- 공지 ----------
    @staticmethod
    def notice_created(
            session: AsyncSession,
            *,
            notice_id: UUID,
            project_id: UUID,
            title: str,
            detail: str | None,
            recipient_ids: list[UUID],
    ) -> None:
        NotificationEvents._notice_event(
            session,
            event_type=NotificationEventType.NOTICE_CREATED,
            notice_id=notice_id, project_id=project_id,
            title=title, detail=detail, recipient_ids=recipient_ids,
        )

    @staticmethod
    def notice_updated(
            session: AsyncSession,
            *,
            notice_id: UUID,
            project_id: UUID,
            title: str,
            detail: str | None,
            recipient_ids: list[UUID],
    ) -> None:
        NotificationEvents._notice_event(
            session,
            event_type=NotificationEventType.NOTICE_UPDATED,
            notice_id=notice_id, project_id=project_id,
            title=title, detail=detail, recipient_ids=recipient_ids,
        )

    @staticmethod
    def _notice_event(session, *, event_type, notice_id, project_id, title, detail, recipient_ids):
        if not recipient_ids:
            return
        OutboxEventRepository(session).enqueue(
            event_type=event_type,
            title=title,
            detail=detail,
            target_type=NotificationTargetType.NOTICE,
            target_id=notice_id,
            project_id=project_id,
            recipient_ids=recipient_ids,
        )

    # ---------- 프로젝트 ----------
    @staticmethod
    def project_invited(session, *, project_id, project_name, recipient_ids):
        NotificationEvents._project_event(session, event_type=NotificationEventType.PROJECT_INVITED, project_id=project_id, project_name=project_name, recipient_ids=recipient_ids)

    @staticmethod
    def project_member_joined(session, *, project_id, project_name, recipient_ids):
        NotificationEvents._project_event(session, event_type=NotificationEventType.PROJECT_MEMBER_JOINED, project_id=project_id, project_name=project_name, recipient_ids=recipient_ids)

    @staticmethod
    def project_invitation_declined(session, *, project_id, project_name, recipient_ids):
        NotificationEvents._project_event(session, event_type=NotificationEventType.PROJECT_INVITATION_DECLINED, project_id=project_id, project_name=project_name, recipient_ids=recipient_ids)

    @staticmethod
    def project_member_removed(session, *, project_id, project_name, recipient_ids):
        NotificationEvents._project_event(session, event_type=NotificationEventType.PROJECT_MEMBER_REMOVED, project_id=project_id, project_name=project_name, recipient_ids=recipient_ids)

    @staticmethod
    def project_leadership_transferred(session, *, project_id, project_name, recipient_ids):
        NotificationEvents._project_event(session, event_type=NotificationEventType.PROJECT_LEADERSHIP_TRANSFERRED, project_id=project_id, project_name=project_name, recipient_ids=recipient_ids)

    @staticmethod
    def _project_event(session, *, event_type, project_id, project_name, recipient_ids):
        if not recipient_ids:
            return
        OutboxEventRepository(session).enqueue(
            event_type=event_type,
            title=project_name,
            detail=None,
            target_type=NotificationTargetType.PROJECT,
            target_id=project_id,
            project_id=project_id,
            recipient_ids=recipient_ids,
        )

    # ---------- 작업 ----------
    @staticmethod
    def work_assigned(session, *, work_id, project_id, title, recipient_ids):
        NotificationEvents._work_event(session, event_type=NotificationEventType.WORK_ASSIGNED, work_id=work_id, project_id=project_id, title=title, recipient_ids=recipient_ids)

    @staticmethod
    def work_status_changed(session, *, work_id, project_id, title, recipient_ids):
        NotificationEvents._work_event(session, event_type=NotificationEventType.WORK_STATUS_CHANGED, work_id=work_id, project_id=project_id, title=title, recipient_ids=recipient_ids)

    @staticmethod
    def _work_event(session, *, event_type, work_id, project_id, title, recipient_ids):
        if not recipient_ids:
            return
        OutboxEventRepository(session).enqueue(
            event_type=event_type,
            title=title,
            detail=None,
            target_type=NotificationTargetType.WORK,
            target_id=work_id,
            project_id=project_id,
            recipient_ids=recipient_ids,
        )
