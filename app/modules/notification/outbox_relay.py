import asyncio
import json
import logging

from app.core.database import AsyncSessionDocker
from app.core.redis import redis_client
from app.modules.notification.constants import OUTBOX_BATCH_SIZE, NOTIFICATION_STREAM_NAME, OUTBOX_POLL_INTERVAL_SECONDS
from app.modules.notification.repository import OutboxEventRepository


logger = logging.getLogger(__name__)

async def run_outbox_relay():
    logger.info("Outbox relay 시작됨")
    while True:
        try:
            async with AsyncSessionDocker() as session:
                repository = OutboxEventRepository(session)
                pending_events = await repository.get_undispatched(limit=OUTBOX_BATCH_SIZE)

                for event in pending_events:
                    try:
                        await redis_client.xadd(NOTIFICATION_STREAM_NAME, {"data": json.dumps(event.payload)})
                        await repository.mark_dispatched(event)
                    except Exception as e:
                        logger.error(f"outbox event {event.id} 발행 실패, 다음 폴링에서 재시도: {e}")
                        await repository.mark_failed(event)

                await session.commit()
                processed_count = len(pending_events)
        except asyncio.CancelledError:
            logger.info("Outbox relay 정지됨")
            raise
        except Exception as e:
            logger.error(f"Outbox relay 배치 처리 중 오류: {e}")
            processed_count = 0

        await asyncio.sleep(0 if processed_count >= OUTBOX_BATCH_SIZE else OUTBOX_POLL_INTERVAL_SECONDS)