from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.exceptions import AppError
from app.core.security import decode_token
from app.modules.member.dependencies import CurrentMemberDep, MemberServiceDep
from app.modules.notification.dependencies import NotificationServiceDep
from app.modules.notification.realtime import manager
from app.modules.notification.schemas import NotificationOut, UnreadCountOut
from app.shared.schemas import ApiResponse, PageOut

router = APIRouter(prefix="/notifications", tags=["Notification"])


@router.get(
    path="",
    response_model=ApiResponse[PageOut[NotificationOut]],
    summary="내 알림 목록 조회",
    description="현재 로그인한 회원에게 온 알림 목록을 조회합니다.",
)
async def list_notifications(
        current_member: CurrentMemberDep,
        service: NotificationServiceDep,
        unread_only: Annotated[bool, Query(description="읽지 않은 알림만 조회")] = False,
        page: Annotated[int, Query(ge=1, description="페이지 번호")] = 1,
        size: Annotated[int, Query(ge=1, le=100, description="페이지 크기")] = 20,
):
    result = await service.list(current_member.id, page=page, size=size, unread_only=unread_only)

    return ApiResponse.success(
        code="NOTIFICATION_LIST_FETCHED",
        message="알림 목록 조회 성공",
        data=PageOut[NotificationOut](
            items=[NotificationOut.from_recipient(item) for item in result["items"]],
            page=result["page"],
            size=result["size"],
            total=result["total"],
        )
    )


@router.get(
    path="/unread-count",
    response_model=ApiResponse[UnreadCountOut],
    summary="읽지 않은 알림 개수 조회",
)
async def get_unread_count(current_member: CurrentMemberDep, service: NotificationServiceDep):
    count = await service.unread_count(current_member.id)
    return ApiResponse.success(
        code="NOTIFICATION_UNREAD_COUNT_FETCHED",
        message="읽지 않은 알림 개수 조회 성공",
        data=UnreadCountOut(count=count),
    )


@router.patch(
    path="/{recipient_id}/read",
    response_model=ApiResponse[NotificationOut],
    summary="알림 읽음 처리",
)
async def mark_notification_read(
        recipient_id: UUID,
        current_member: CurrentMemberDep,
        service: NotificationServiceDep,
):
    recipient = await service.mark_read(recipient_id, current_member.id)
    return ApiResponse.success(
        code="NOTIFICATION_READ",
        message="알림 읽음 처리 성공",
        data=NotificationOut.from_recipient(recipient),
    )


@router.patch(
    path="/read-all",
    response_model=ApiResponse[None],
    summary="모든 알림 읽음 처리",
)
async def mark_all_notifications_read(current_member: CurrentMemberDep, service: NotificationServiceDep):
    await service.mark_all_read(current_member.id)
    return ApiResponse.success(
        code="NOTIFICATION_ALL_READ",
        message="모든 알림 읽음 처리 성공",
        data=None,
    )


async def _get_ws_current_member_id(token: str, member_service: MemberServiceDep) -> UUID:
    """WebSocket용 토큰 인증 (쿼리 파라미터 기반). chat.router의 방식과 동일."""
    try:
        payload = decode_token(token)
        member_id = payload.get("sub")
        if not member_id:
            raise Exception("Invalid token")
        member = await member_service.get(UUID(member_id))
        if not member:
            raise Exception("Member not found")
        return member.id
    except Exception:
        raise AppError.unauthorized("WebSocket 인증 실패")


@router.websocket("/ws")
async def notification_websocket(
        member_service: MemberServiceDep,
        websocket: WebSocket,
        token: Annotated[str, Query()],
):
    """
    실시간 알림 수신용 WebSocket.
    연결돼 있으면 새 알림이 발생하는 즉시 push되고, 연결이 없어도 알림은 DB에 쌓여
    REST(GET /notifications)로 언제든 조회할 수 있다.
    """
    await websocket.accept()

    try:
        member_id = await _get_ws_current_member_id(token, member_service)
    except Exception:
        await websocket.close(code=1008)  # Policy Violation
        return

    await manager.connect(member_id, websocket)

    try:
        while True:
            # 클라이언트가 보내는 메시지는 사용하지 않지만, 연결 종료를 감지하기 위해 대기한다.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(member_id, websocket)
    except Exception:
        manager.disconnect(member_id, websocket)
        await websocket.close(code=1011)  # Internal Error
