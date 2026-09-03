"""
Redis Stream 컨슈머.

Consumer Group(GROUP_NAME)으로 읽기 때문에, API 인스턴스가 여러 대 떠 있어도
같은 스트림 엔트리는 그 중 정확히 한 인스턴스에서만 처리된다 (competing consumers).
처리 중 예외가 나면 XACK을 하지 않으므로 해당 엔트리는 pending 상태로 남아
재시도 대상이 된다.

FastAPI 앱의 lifespan에서 outbox_relay와 함께 백그라운드 task로 돌아간다.
"""
import asyncio
import json
import logging
import socket
import uuid
from uuid import UUID

import redis.exceptions

from app.core.database import AsyncSessionDocker
from app.core.redis import redis_client
from app.modules.notification.outbox_relay import STREAM_NAME
from app.modules.notification.realtime import manager as notification_manager
from app.modules.notification.repository import NotificationRepository

logger = logging.getLogger(__name__)

GROUP_NAME = "notification-workers"
CONSUMER_NAME = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"


async def _ensure_group():
    try:
        await redis_client.xgroup_create(STREAM_NAME, GROUP_NAME, id="0", mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


async def _handle_message(message_id: str, fields: dict):
    payload = json.loads(fields["data"])
    recipient_ids = [UUID(m) for m in payload.get("recipient_ids", [])]

    if not recipient_ids:
        await redis_client.xack(STREAM_NAME, GROUP_NAME, message_id)
        return

    async with AsyncSessionDocker() as session:
        notification = await NotificationRepository(session).create_with_recipients(
            event_type=payload["event_type"],
            title=payload["title"],
            detail=payload.get("detail"),
            target_type=payload["target_type"],
            target_id=UUID(payload["target_id"]) if payload.get("target_id") else None,
            recipient_ids=recipient_ids,
        )

    realtime_payload = {
        "notification_id": str(notification.id),
        "event_type": notification.event_type,
        "title": notification.title,
        "detail": notification.detail,
        "target_type": notification.target_type,
        "target_id": str(notification.target_id) if notification.target_id else None,
        "created_at": notification.created_at.isoformat(),
    }
    for member_id in recipient_ids:
        await notification_manager.publish(member_id, realtime_payload)

    await redis_client.xack(STREAM_NAME, GROUP_NAME, message_id)


async def run_notification_consumer():
    await _ensure_group()
    logger.info(f"Notification consumer '{CONSUMER_NAME}' started")

    while True:
        try:
            response = await redis_client.xreadgroup(
                GROUP_NAME,
                CONSUMER_NAME,
                {STREAM_NAME: ">"},
                count=10,
                block=5000,
            )
            for _stream_name, messages in response:
                for message_id, fields in messages:
                    try:
                        await _handle_message(message_id, fields)
                    except Exception as e:
                        logger.error(f"notification event {message_id} 처리 실패 (재시도 대상으로 남김): {e}")
        except asyncio.CancelledError:
            logger.info("Notification consumer stopped")
            raise
        except Exception as e:
            logger.error(f"Notification consumer 루프 오류: {e}")
            await asyncio.sleep(1)
