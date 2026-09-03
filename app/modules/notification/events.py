"""
다른 모듈(notice, project, work 등)이 "이런 일이 있었다"를 알릴 때 호출하는 단일 진입점.

여기서 하는 일은 Outbox 테이블에 행 하나를 남기는 것뿐이며, 커밋은 호출부가 한다.
=> notice 모듈이 notification 테이블을 직접 건드리지 않고, 오직 이 이벤트 API를 통해서만 통신한다.
실제 브로커 발행/알림 생성/실시간 push는 app.modules.notification.outbox_relay / consumer 가 담당한다.

새 이벤트를 추가하고 싶다면 이 클래스에 메서드 하나만 추가하면 된다(예: work_created).
"""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notification.repository import OutboxRepository
from app.shared.enums import NotificationTargetType


class NotificationEvents:
    @staticmethod
    def notice_created(
        session: AsyncSession,
        *,
        notice_id: UUID,
        title: str,
        detail: str | None,
        recipient_ids: list[UUID],
    ) -> None:
        """프로젝트에 공지가 등록되었을 때 프로젝트 멤버 전원에게 팬아웃."""
        OutboxRepository(session).enqueue(
            event_type="notice.created",
            title=f"[공지] {title}",
            detail=detail,
            target_type=NotificationTargetType.NOTICE,
            target_id=notice_id,
            recipient_ids=recipient_ids,
        )

    @staticmethod
    def project_invited(
        session: AsyncSession,
        *,
        invitation_id: UUID,
        project_name: str,
        invitee_id: UUID,
    ) -> None:
        """프로젝트 초대장이 생성되었을 때 초대받은 회원 1명에게만 전달."""
        OutboxRepository(session).enqueue(
            event_type="project.invited",
            title=f"[초대] '{project_name}' 프로젝트에 초대되었습니다.",
            detail=None,
            target_type=NotificationTargetType.INVITATION,
            target_id=invitation_id,
            recipient_ids=[invitee_id],
        )
