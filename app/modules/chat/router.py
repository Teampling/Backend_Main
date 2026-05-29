from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query

from app.modules.chat.service import ChatService, manager
from app.modules.chat.dependencies import get_chat_service
from app.modules.chat.schemas import ChatRoomRead, ChatMessageRead, DirectChatRoomCreate, ChatRoomDetailRead
from app.modules.member.dependencies import CurrentMemberDep, get_member_service, MemberServiceDep
from app.modules.project.dependencies import ProjectParticipantDep
from app.modules.member.models import Member
from app.core.exceptions import AppError
from app.core.security import decode_token

router = APIRouter(prefix="/chat", tags=["chat"])

@router.get("/projects/{project_id}/rooms", response_model=list[ChatRoomRead])
async def list_rooms(
    project_id: UUID,
    current_member: CurrentMemberDep,
    _project: ProjectParticipantDep,
    service: ChatService = Depends(get_chat_service)
):
    """프로젝트 내 채팅방 목록을 조회합니다."""
    return await service.list_rooms(project_id, current_member.id)

@router.post("/projects/{project_id}/rooms/direct", response_model=ChatRoomRead)
async def create_direct_room(
    project_id: UUID,
    data: DirectChatRoomCreate,
    current_member: CurrentMemberDep,
    _project: ProjectParticipantDep,
    service: ChatService = Depends(get_chat_service)
):
    """1:1 채팅방을 생성하거나 기존 방을 반환합니다."""
    return await service.get_or_create_direct_room(project_id, current_member.id, data.target_member_id)

@router.get("/rooms/{room_id}/messages", response_model=list[ChatMessageRead])
async def get_messages(
    room_id: UUID,
    current_member: CurrentMemberDep,
    limit: int = 50,
    offset: int = 0,
    service: ChatService = Depends(get_chat_service)
):
    """채팅 이력을 조회합니다."""
    return await service.get_history(room_id, current_member.id, limit, offset)

@router.delete("/rooms/{room_id}")
async def delete_room(
    room_id: UUID,
    current_member: CurrentMemberDep,
    service: ChatService = Depends(get_chat_service)
):
    """채팅방을 삭제합니다."""
    await service.delete_room(room_id, current_member.id)
    return {"message": "채팅방이 삭제되었습니다."}

async def get_ws_current_member(
    token: str,
    member_service: MemberServiceDep
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
    member_service: MemberServiceDep,
    websocket: WebSocket,
    room_id: UUID,
    token: Annotated[str, Query()],
    chat_service: ChatService = Depends(get_chat_service),
):
    # 인증
    try:
        current_member = await get_ws_current_member(token, member_service)
    except Exception:
        await websocket.close(code=1008) # Policy Violation
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
                content=data
            )
            
            # 브로드캐스트용 데이터 구성
            msg_data = ChatMessageRead.model_validate(message).model_dump(mode="json")
            
            # Redis를 통해 전체 서버 인스턴스로 발행
            await manager.publish(room_id, msg_data)
            
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
    except Exception as e:
        # 기타 에러 발생 시 연결 종료
        manager.disconnect(room_id, websocket)
        await websocket.close(code=1011) # Internal Error
