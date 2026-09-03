import asyncio
import json
import logging
from uuid import UUID

from fastapi import WebSocket

from app.core.redis import redis_client

logger = logging.getLogger(__name__)


class NotificationConnectionManager:
    """
    회원별 실시간 알림 push 관리자.
    app.modules.chat.service.ConnectionManager와 동일한 패턴이다 — 채널 키만
    room_id 대신 member_id를 쓴다.

    인스턴스가 여러 대로 스케일아웃되어도, 알림 컨슈머가 어느 인스턴스에서 뜨든
    Redis Pub/Sub(`notify:{member_id}`)을 거쳐 실제로 그 회원이 연결돼 있는 인스턴스로
    전달된다 — 서버 인스턴스 로컬 메모리(active_connections)만으로는 불가능한 부분.
    """

    def __init__(self):
        self.active_connections: dict[UUID, set[WebSocket]] = {}
        self.sub_tasks: dict[UUID, asyncio.Task] = {}

    async def connect(self, member_id: UUID, websocket: WebSocket):
        if member_id not in self.active_connections:
            self.active_connections[member_id] = set()
            self.sub_tasks[member_id] = asyncio.create_task(self._subscribe(member_id))

        self.active_connections[member_id].add(websocket)

    def disconnect(self, member_id: UUID, websocket: WebSocket):
        if member_id in self.active_connections:
            self.active_connections[member_id].discard(websocket)
            if not self.active_connections[member_id]:
                if member_id in self.sub_tasks:
                    self.sub_tasks[member_id].cancel()
                    del self.sub_tasks[member_id]
                del self.active_connections[member_id]

    async def _subscribe(self, member_id: UUID):
        pubsub = redis_client.pubsub()
        channel = f"notify:{member_id}"
        await pubsub.subscribe(channel)

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await self._local_broadcast(member_id, data)
        except asyncio.CancelledError:
            await pubsub.unsubscribe(channel)
        except Exception as e:
            logger.error(f"Notification subscription error for member {member_id}: {e}")
            await pubsub.unsubscribe(channel)

    async def _local_broadcast(self, member_id: UUID, message: dict):
        if member_id in self.active_connections:
            for connection in list(self.active_connections[member_id]):
                try:
                    await connection.send_json(message)
                except Exception:
                    self.active_connections[member_id].discard(connection)

    @staticmethod
    async def publish(member_id: UUID, message: dict):
        """알림 컨슈머가 새 알림을 특정 회원에게 실시간으로 밀어넣을 때 호출."""
        await redis_client.publish(f"notify:{member_id}", json.dumps(message))


manager = NotificationConnectionManager()
