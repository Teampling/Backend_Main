from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query, WebSocket, WebSocketDisconnect

from app.modules.chat.dependencies import ChatServiceDep
from app.modules.chat.service import manager
from app.modules.chat.schemas import ChatRoomOut, ChatMessageOut, DirectChatRoomCreateIn
from app.modules.member.dependencies import CurrentMemberDep, MemberServiceDep
from app.modules.member.models import Member
from app.modules.project.dependencies import ProjectParticipantDep
from app.core.exceptions import AppError
from app.core.security import decode_token
from app.shared.schemas import ApiResponse

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get(
    path="/projects/{project_id}/rooms",
    response_model=ApiResponse[list[ChatRoomOut]],
    summary="채팅방 목록 조회",
    description="프로젝트 내에서 현재 회원이 참여 중인 채팅방 목록을 조회합니다.",
)
async def list_rooms(
        service: ChatServiceDep,
        current_member: CurrentMemberDep,
        _project: ProjectParticipantDep,
        project_id: Annotated[UUID, Path(description="조회할 프로젝트 ID")],
):
    rooms = await service.list_rooms(project_id, current_member.id)
    return ApiResponse.success(
        code="CHAT_ROOM_LIST_FETCHED",
        message="채팅방 목록 조회 성공",
        data=rooms,
    )


@router.post(
    path="/projects/{project_id}/rooms/direct",
    response_model=ApiResponse[ChatRoomOut],
    summary="1:1 채팅방 생성",
    description="1:1 채팅방을 생성하거나 기존 방을 반환합니다.",
)
async def create_direct_room(
        service: ChatServiceDep,
        current_member: CurrentMemberDep,
        _project: ProjectParticipantDep,
        project_id: Annotated[UUID, Path(description="프로젝트 ID")],
        data: DirectChatRoomCreateIn,
):
    room = await service.get_or_create_direct_room(project_id, current_member.id, data.target_member_id)
    return ApiResponse.success(
        code="CHAT_DIRECT_ROOM_CREATED",
        message="1:1 채팅방 생성 성공",
        data=ChatRoomOut.model_validate(room),
    )


@router.get(
    path="/rooms/{room_id}/messages",
    response_model=ApiResponse[list[ChatMessageOut]],
    summary="채팅 이력 조회",
    description="채팅방의 메시지 이력을 페이지네이션으로 조회합니다.",
)
async def get_messages(
        service: ChatServiceDep,
        current_member: CurrentMemberDep,
        room_id: Annotated[UUID, Path(description="채팅방 ID")],
        limit: Annotated[int, Query(ge=1, le=100, description="조회 개수")] = 50,
        offset: Annotated[int, Query(ge=0, description="조회 시작 위치")] = 0,
):
    messages = await service.get_history(room_id, current_member.id, limit, offset)
    return ApiResponse.success(
        code="CHAT_MESSAGE_LIST_FETCHED",
        message="채팅 이력 조회 성공",
        data=[ChatMessageOut.model_validate(message) for message in messages],
    )


@router.delete(
    path="/rooms/{room_id}",
    response_model=ApiResponse[None],
    summary="채팅방 삭제",
    description="1:1 채팅방을 삭제합니다. 단체 채팅방은 삭제할 수 없습니다.",
)
async def delete_room(
        service: ChatServiceDep,
        current_member: CurrentMemberDep,
        room_id: Annotated[UUID, Path(description="삭제할 채팅방 ID")],
):
    await service.delete_room(room_id, current_member.id)
    return ApiResponse.success(
        code="CHAT_ROOM_DELETED",
        message="채팅방 삭제 성공",
        data=None,
    )


@router.post(
    path="/rooms/{room_id}/read/{message_id}",
    response_model=ApiResponse[None],
    summary="채팅방 메시지 읽음 처리",
    description="채팅방에서 특정 메시지를 가장 최근에 읽은 메시지로 처리합니다.",
)
async def mark_as_read(
        service: ChatServiceDep,
        current_member: CurrentMemberDep,
        room_id: Annotated[UUID, Path(description="채팅방 ID")],
        message_id: Annotated[UUID, Path(description="읽음 처리할 메시지 ID")],
):
    await service.mark_as_read(room_id, current_member.id, message_id)
    return ApiResponse.success(
        code="CHAT_MESSAGE_MARKED_AS_READ",
        message="메시지 읽음 처리 성공",
        data=None,
    )


async def get_ws_current_member(
        token: str,
        member_service: MemberServiceDep,
) -> Member:
    """WebSocket용 토큰 인증 (쿼리 파라미터 기반)"""
    try:
        payload = decode_token(token)
        member_id = payload.get("sub")
        if not member_id:
            raise Exception("Invalid token")
        member = await member_service.get(UUID(member_id))
        if not member:
            raise Exception("Member not found")
        return member
    except Exception:
        raise AppError.unauthorized("WebSocket 인증 실패")


@router.websocket("/ws/{room_id}")
async def chat_websocket(
        websocket: WebSocket,
        room_id: UUID,
        token: Annotated[str, Query()],
        member_service: MemberServiceDep,
        chat_service: ChatServiceDep,
):
    # 핸드쉐이크 먼저 수락
    await websocket.accept()

    # 인증
    try:
        current_member = await get_ws_current_member(token, member_service)
    except Exception:
        await websocket.close(code=1008)  # Policy Violation
        return

    # 연결
    await manager.connect(room_id, websocket)

    try:
        while True:
            # 클라이언트로부터 메시지 대기
            data = await websocket.receive_text()

            # 메시지 저장
            # TODO: 메시지 타입(TEXT, IMAGE 등) 처리 추가 가능
            message = await chat_service.send_message(
                room_id=room_id,
                sender_id=current_member.id,
                content=data,
            )

            # 브로드캐스트용 데이터 구성
            msg_data = ChatMessageOut.model_validate(message).model_dump(mode="json")

            # Redis를 통해 전체 서버 인스턴스로 발행
            await manager.publish(room_id, msg_data)

    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
    except Exception:
        # 기타 에러 발생 시 연결 종료
        manager.disconnect(room_id, websocket)
        await websocket.close(code=1011)  # Internal Error
