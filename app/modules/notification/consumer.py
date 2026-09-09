import asyncio
import json
import logging
from uuid import UUID

import redis

from app.core.database import AsyncSessionDocker
from app.core.redis import redis_client
from app.modules.notification.constants import (
    NOTIFICATION_STREAM_NAME,
    NOTIFICATION_GROUP_NAME,
    CONSUMER_NAME,
    CONSUMER_READ_COUNT,
    CONSUMER_BLOCK_MS,
)
from app.modules.notification.manager import notification_manager
from app.modules.notification.repository import NotificationRepository
from app.shared.enums import NotificationTargetType, NotificationEventType

logger = logging.getLogger(__name__)

async def _handle_message(message_id: str, fields: dict):
    payload = json.loads(fields["data"])
    recipient_ids = [UUID(id) for id in payload.get("recipient_ids", [])]

    if not recipient_ids:
        await redis_client.xack(NOTIFICATION_STREAM_NAME, NOTIFICATION_GROUP_NAME, message_id)
        return

    async with AsyncSessionDocker() as session:
        notification = await NotificationRepository(session).create(
            event_type=NotificationEventType(payload["event_type"]),
            title=payload["title"],
            detail=payload["detail"],
            target_type=NotificationTargetType(payload["target_type"]),
            target_id=UUID(payload["target_id"]) if payload["target_id"] else None,
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

        await session.commit()

    await redis_client.xack(NOTIFICATION_STREAM_NAME, NOTIFICATION_GROUP_NAME, message_id)

    try:
        for member_id in recipient_ids:
            await notification_manager.publish(member_id, realtime_payload)
    except Exception as e:
        logger.warning(f"알림 실시간 발행 실패 후 넘어감(Notification ID: {realtime_payload['notification_id']}): {e}")

async def run_notification_consumer():
    # XGROUP 생성 시도, 이미 존재하면 무시
    try:
        await redis_client.xgroup_create(NOTIFICATION_STREAM_NAME, NOTIFICATION_GROUP_NAME, id="$", mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
    logger.info(f"Notification 컨슈머 '{CONSUMER_NAME}' 시작됨")

    while True:
        try:
            response = await redis_client.xreadgroup(
                NOTIFICATION_GROUP_NAME,
                CONSUMER_NAME,
                {NOTIFICATION_STREAM_NAME: ">"},
                count=CONSUMER_READ_COUNT,
                block=CONSUMER_BLOCK_MS,
            )
            if not response:
                continue
            for stream_name, messages in response:
                for message_id, fields in messages:
                    try:
                        await _handle_message(message_id, fields)
                    except Exception as e:
                        logger.error(f"Notification 이벤트 {message_id} 처리 실패 (재시도 대상으로 남김): {e}")
        except asyncio.CancelledError:
            logger.info("Notification 컨슈머 종료됨")
            raise
        except Exception as e:
            logger.error(f"Notification 컨슈머 루프 오류: {e}")
            await asyncio.sleep(1)