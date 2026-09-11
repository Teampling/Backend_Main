from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.core.security import decode_token
from app.modules.member.dependencies import CurrentMemberDep
from app.modules.notification.dependencies import NotificationServiceDep
from app.modules.notification.realtime import notification_manager
from app.modules.notification.schemas import NotificationOut, UnreadCountOut
from app.shared.schemas import ApiResponse, PageOut


router = APIRouter(prefix="/notifications", tags=["Notification"])

@router.get(
    path="",
    response_model=ApiResponse[PageOut[NotificationOut]],
    summary="내 알림 목록 조회",
    description="현재 로그인한 회원에게 온 알림 목록을 최신순으로 조회합니다.",
)
async def list_my_notifications(
        current_member: CurrentMemberDep,
        service: NotificationServiceDep,
        page: Annotated[int, Query(ge=1, description="페이지 번호")] = 1,
        size: Annotated[int, Query(ge=1, le=100, description="페이지 크기")] = 50,
        unread_only: Annotated[bool, Query(description="안 읽은 알림만 조회")] = False,
):
    result = await service.list_by_member(
        current_member.id,
        page=page,
        size=size,
        unread_only=unread_only,
    )
    return ApiResponse.success(
        code="NOTIFICATION_LIST_FETCHED",
        message="알림 목록 조회 성공",
        data=PageOut[NotificationOut](
            items=[NotificationOut.from_recipient(r) for r in result["items"]],
            page=result["page"],
            size=result["size"],
            total=result["total"],
        ),
    )

@router.get(
    path="/count/unread",
    response_model=ApiResponse[UnreadCountOut],
    summary="안 읽은 알림 개수 조회",
    description="현재 로그인한 회원의 안 읽은 알림 개수를 조회합니다.",
)
async def get_unread_count(
        current_member: CurrentMemberDep,
        service: NotificationServiceDep,
):
    count = await service.count_unread(current_member.id)
    return ApiResponse.success(
        code="NOTIFICATION_UNREAD_COUNT_FETCHED",
        message="안 읽은 알림 개수 조회 성공",
        data=UnreadCountOut(count=count),
    )

@router.patch(
    path="/read/all",
    response_model=ApiResponse[None],
    summary="모든 알림 읽음 처리",
    description="현재 로그인한 회원의 안 읽은 알림을 모두 읽음 처리합니다.",
)
async def mark_all_notifications_read(
        current_member: CurrentMemberDep,
        service: NotificationServiceDep,
):
    count = await service.mark_all_read(current_member.id)
    return ApiResponse.success(
        code="NOTIFICATION_ALL_READ",
        message=f"알림 {count}건 읽음 처리 성공",
        data=None,
    )

@router.patch(
    path="/read/one/{notification_id}",
    response_model=ApiResponse[None],
    summary="알림 읽음 처리",
    description="현재 로그인한 회원의 특정 알림을 읽음 처리합니다.",
)
async def mark_notification_read(
        current_member: CurrentMemberDep,
        service: NotificationServiceDep,
        notification_id: Annotated[UUID, Path(description="읽음 처리할 알림 ID")],
):
    await service.mark_read(current_member.id, notification_id)
    return ApiResponse.success(
        code="NOTIFICATION_READ",
        message="알림 읽음 처리 성공",
        data=None,
    )

@router.websocket("/ws")
async def notification_websocket(
        websocket: WebSocket,
        token: Annotated[str, Query(description="WebSocket 인증 토큰")],
):
    await websocket.accept()

    try:
        payload = decode_token(token)
        member_id = UUID(payload["sub"])
    except Exception:
        await websocket.close(code=1008)  # Policy Violation (인증 실패)
        return

    await notification_manager.connect(member_id, websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_manager.disconnect(member_id, websocket)