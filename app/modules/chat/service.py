import json
import asyncio
import logging
from uuid import UUID
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import WebSocket

from app.modules.chat.repository import ChatRepository
from app.modules.chat.models import ChatRoom, ChatMessage
from app.modules.chat.schemas import ChatRoomOut, ChatMessageOut
from app.shared.enums import ChatRoomType
from app.core.exceptions import AppError
from app.core.redis import redis_client

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # room_id -> set of websockets
        self.active_connections: dict[UUID, set[WebSocket]] = {}
        # room_id -> redis subscriber task
        self.sub_tasks: dict[UUID, asyncio.Task] = {}

    async def connect(self, room_id: UUID, websocket: WebSocket):
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()
            # 해당 방에 대한 첫 연결이면 Redis 구독 시작
            self.sub_tasks[room_id] = asyncio.create_task(self._subscribe_room(room_id))
        
        self.active_connections[room_id].add(websocket)

    def disconnect(self, room_id: UUID, websocket: WebSocket):
        if room_id in self.active_connections:
            self.active_connections[room_id].discard(websocket)
            if not self.active_connections[room_id]:
                # 더 이상 연결된 세션이 없으면 구독 중단
                if room_id in self.sub_tasks:
                    self.sub_tasks[room_id].cancel()
                    del self.sub_tasks[room_id]
                del self.active_connections[room_id]

    async def _subscribe_room(self, room_id: UUID):
        """Redis 채널을 구독하고 메시지가 오면 해당 방의 모든 WebSocket으로 브로드캐스트합니다."""
        pubsub = redis_client.pubsub()
        channel_name = f"chat:{room_id}"
        await pubsub.subscribe(channel_name)
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await self._local_broadcast(room_id, data)
        except asyncio.CancelledError:
            await pubsub.unsubscribe(channel_name)
        except Exception as e:
            logger.error(f"Redis subscription error for room {room_id}: {e}")
            await pubsub.unsubscribe(channel_name)

    async def _local_broadcast(self, room_id: UUID, message: dict):
        """현재 서버 인스턴스에 연결된 WebSocket들에게만 메시지를 전송합니다."""
        if room_id in self.active_connections:
            targets = list(self.active_connections[room_id])
            for connection in targets:
                try:
                    await connection.send_json(message)
                except Exception:
                    self.active_connections[room_id].discard(connection)

    async def publish(self, room_id: UUID, message: dict):
        """Redis 채널에 메시지를 발행합니다 (전체 서버 인스턴스로 확산)."""
        await redis_client.publish(f"chat:{room_id}", json.dumps(message))

    def _presence_key(self, room_id: UUID) -> str:
        return f"presence:room:{room_id}"

    async def add_presence(self, room_id: UUID, member_id: UUID) -> int:
        """연결 수 +1, 갱신된 연결 수 반환. 1이면 '방금 온라인 됨'"""
        count = await redis_client.hincrby(self._presence_key(room_id), str(member_id), 1)
        return count

    async def remove_presence(self, room_id: UUID, member_id: UUID) -> int:
        """연결 수 -1, 0 이하면 필드 삭제. 0이면 '방금 오프라인 됨'"""
        key = self._presence_key(room_id)
        count = await redis_client.hincrby(key, str(member_id), -1)
        if count <= 0:
            await redis_client.hdel(key, str(member_id))
            return 0
        return count

    async def is_present(self, room_id: UUID, member_id: UUID) -> bool:
        return await redis_client.hexists(self._presence_key(room_id), str(member_id))

    async def enter_presence(self, room_id: UUID, member_id: UUID, username: str) -> None:
        """focus 시 호출: presence 등록, 첫 진입이면 online 브로드캐스트"""
        first = await self.add_presence(room_id, member_id)
        if first == 1:
            await self.publish(room_id, {
                "type": "presence",
                "data": {
                    "room_id": str(room_id),
                    "member_id": str(member_id),
                    "username": username,
                    "online": True,
                },
            })

    async def leave_presence(self, room_id: UUID, member_id: UUID, username: str) -> None:
        """blur/disconnect 시 호출: presence 해제, 마지막이면 offline 브로드캐스트"""
        last = await self.remove_presence(room_id, member_id)
        if last == 0:
            await self.publish(room_id, {
                "type": "presence",
                "data": {
                    "room_id": str(room_id),
                    "member_id": str(member_id),
                    "username": username,
                    "online": False,
                },
            })

    async def switch_focus(self, member_id: UUID, username: str, old_room: UUID | None, new_room: UUID | None) -> None:
        """보던 방(old)에서 나가고 새 방(new)으로 focus 이동"""
        if old_room == new_room:
            return
        if old_room is not None:
            await self.leave_presence(old_room, member_id, username)
        if new_room is not None:
            await self.enter_presence(new_room, member_id, username)

manager = ConnectionManager()

class ChatService:
    def __init__(self, session: AsyncSession, repository: ChatRepository):
        self.session = session
        self.repository = repository

    async def get_or_create_group_room(self, project_id: UUID) -> ChatRoom:
        """프로젝트의 단체 채팅방을 조회하거나 없으면 생성합니다."""
        room = await self.repository.get_group_room(project_id)
        if not room:
            room = ChatRoom(
                project_id=project_id,
                type=ChatRoomType.GROUP,
                name="단체 채팅방"
            )
            room = await self.repository.save_room(room)
            await self.session.commit()
            # members가 포함된 상태로 다시 조회
            room = await self.repository.get_room_by_id(room.id)
        return room

    async def get_or_create_direct_room(self, project_id: UUID, member_a: UUID, member_b: UUID) -> ChatRoom:
        """두 멤버 간의 1:1 채팅방을 조회하거나 없으면 생성합니다."""
        if member_a == member_b:
            raise AppError.bad_request("자기 자신과는 대화할 수 없습니다.")

        room = await self.repository.get_direct_room(project_id, member_a, member_b)
        if not room:
            room = ChatRoom(
                project_id=project_id,
                type=ChatRoomType.DIRECT
            )
            room = await self.repository.save_room(room)
            # 멤버 추가
            await self.repository.add_member_to_room(room.id, member_a)
            await self.repository.add_member_to_room(room.id, member_b)
            
            await self.session.commit()
            # members가 포함된 상태로 다시 조회
            room = await self.repository.get_room_by_id(room.id)
        return room

    async def send_message(self, room_id: UUID, sender_id: UUID, content: str) -> ChatMessage:
        """메시지를 DB에 저장하고 반환합니다."""
        # 멤버십 확인
        if not await self.repository.is_room_member(room_id, sender_id):
            # 단체 채팅방인 경우 자동 참여 처리 고려 가능하나, 여기서는 에러 처리
            room = await self.repository.get_room_by_id(room_id)
            if not room:
                raise AppError.not_found("채팅방을 찾을 수 없습니다.")
            
            if room.type == ChatRoomType.GROUP:
                # 단체방은 프로젝트 멤버면 자동 참여
                await self.repository.add_member_to_room(room_id, sender_id)
            else:
                raise AppError.forbidden("채팅방 멤버가 아닙니다.")

        message = ChatMessage(
            chat_room_id=room_id,
            sender_id=sender_id,
            content=content
        )
        saved = await self.repository.save_message(message)
        await self.session.commit()
        await self.session.refresh(saved, ["sender"])
        return saved

    async def get_history(self, room_id: UUID, member_id: UUID, limit: int = 50, offset: int = 0):
        """채팅 이력을 조회합니다."""
        if not await self.repository.is_room_member(room_id, member_id):
            raise AppError.forbidden("채팅방 멤버가 아닙니다.")
        
        return await self.repository.get_messages(room_id, limit, offset)

    async def list_rooms(self, project_id: UUID, member_id: UUID) -> list[ChatRoomOut]:
        """참여 중인 채팅방 목록을 조회합니다."""
        group_room = await self.get_or_create_group_room(project_id)

        if not await self.repository.is_room_member(group_room.id, member_id):
            await self.repository.add_member_to_room(group_room.id, member_id)
            await self.session.commit()

        rooms = await self.repository.get_rooms_by_project(project_id, member_id)
        last_messages = await self.repository.get_last_messages([room.id for room in rooms])

        result = []
        for room in rooms:
            count = await self.repository.get_unread_count(room.id, member_id)
            room_data = ChatRoomOut.model_validate(room)
            room_data.unread_count = count
            last = last_messages.get(room.id)
            room_data.last_message = ChatMessageOut.model_validate(last) if last else None
            result.append(room_data)
        return result

    async def delete_room(self, room_id: UUID, member_id: UUID):
        """채팅방을 삭제합니다."""
        room = await self.repository.get_room_by_id(room_id)
        if not room:
            raise AppError.not_found("채팅방을 찾을 수 없습니다.")
        
        if room.type == ChatRoomType.GROUP:
            raise AppError.bad_request("단체 채팅방은 삭제할 수 없습니다.")
        
        if not await self.repository.is_room_member(room_id, member_id):
            raise AppError.forbidden("채팅방 삭제 권한이 없습니다.")
            
        await self.repository.delete_room(room)
        await self.session.commit()

    async def mark_as_read(self, room_id: UUID, member_id: UUID, message_id: UUID) -> None:
        if not await self.repository.is_room_member(room_id, member_id):
            raise AppError.forbidden("채팅방 멤버가 아닙니다.")

        message = await self.repository.get_message_by_id(message_id)
        if not message or message.chat_room_id != room_id:
            raise AppError.not_found("메시지")

        await self.repository.mark_as_read(room_id, member_id, message_id)
        await self.session.commit()