import asyncio
import json
import logging
from uuid import UUID
from fastapi import WebSocket

from app.core.redis import redis_client
from app.modules.notification.constants import NOTIFICATION_CHANNEL_PREFIX


logger = logging.getLogger(__name__)

class NotificationConnectionManager:
    def __init__(self):
        self.active_connections: dict[UUID, set[WebSocket]] = {}
        self.sub_tasks: dict[UUID, asyncio.Task] = {}

    async def connect(self, member_id: UUID, websocket: WebSocket):
        if member_id not in self.active_connections:
            self.active_connections[member_id] = set()
            self.sub_tasks[member_id] = asyncio.create_task(self._subscribe(member_id))

        self.active_connections[member_id].add(websocket)

    def disconnect(self, member_id: UUID, websocket: WebSocket):
        if member_id not in self.active_connections:
            return

        self.active_connections[member_id].discard(websocket)

        if not self.active_connections[member_id]:
            task = self.sub_tasks.pop(member_id, None)
            if task:
                task.cancel()
            del self.active_connections[member_id]

    async def _subscribe(self, member_id: UUID):
        pubsub = redis_client.pubsub()
        channel = f"{NOTIFICATION_CHANNEL_PREFIX}{member_id}"
        try:
            await pubsub.subscribe(channel)
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await self._local_broadcast(member_id, data)
        except asyncio.CancelledError:
            await pubsub.unsubscribe(channel)
        except Exception as e:
            logger.error(f"알림 구독 오류 (member: {member_id}): {e}")
            await pubsub.unsubscribe(channel)

    async def _local_broadcast(self, member_id: UUID, message: dict):
        for connection in list(self.active_connections.get(member_id, set())):
            try:
                await connection.send_json(message)
            except Exception:
                self.active_connections[member_id].discard(connection)

    @staticmethod
    async def publish(member_id: UUID, message: dict):
        await redis_client.publish(f"{NOTIFICATION_CHANNEL_PREFIX}{member_id}", json.dumps(message))

notification_manager = NotificationConnectionManager()