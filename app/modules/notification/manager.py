import json
from uuid import UUID

from app.core.redis import redis_client


class NotificationConnectionManager:

    @staticmethod
    async def publish(member_id: UUID, message: dict):
        await redis_client.publish(f"notify:{member_id}", json.dumps(message))

notification_manager = NotificationConnectionManager()