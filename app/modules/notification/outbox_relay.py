"""
Transactional Outbox 릴레이.

outbox_events 테이블을 폴링해 아직 발행되지 않은(dispatched=False) 이벤트를
Redis Stream으로 옮긴다. Redis가 잠깐 죽어 있어도 이벤트는 Postgres에 그대로
남아있으므로 유실되지 않고, 다음 폴링에서 다시 시도된다 (at-least-once 전달).

FastAPI 앱의 lifespan에서 백그라운드 asyncio task로 계속 돌아간다 (app/main.py 참고).
"""
import asyncio
import json
import logging

from app.core.database import AsyncSessionDocker
from app.core.redis import redis_client
from app.modules.notification.repository import OutboxRepository

logger = logging.getLogger(__name__)

STREAM_NAME = "notifications:stream"
POLL_INTERVAL_SECONDS = 1.0
BATCH_SIZE = 100


async def _dispatch_once() -> int:
    async with AsyncSessionDocker() as session:
        repository = OutboxRepository(session)
        events = await repository.fetch_pending(limit=BATCH_SIZE)

        for event in events:
            try:
                await redis_client.xadd(STREAM_NAME, {"data": json.dumps(event.payload)})
                await repository.mark_dispatched(event)
            except Exception as e:
                logger.error(f"outbox event {event.id} 발행 실패, 다음 폴링에서 재시도: {e}")
                await repository.mark_failed(event)

        await session.commit()
        return len(events)


async def run_outbox_relay():
    logger.info("Outbox relay started")
    while True:
        try:
            dispatched = await _dispatch_once()
        except asyncio.CancelledError:
            logger.info("Outbox relay stopped")
            raise
        except Exception as e:
            logger.error(f"Outbox relay 배치 처리 중 오류: {e}")
            dispatched = 0

        # 방금 배치가 꽉 찼으면(=밀려 있을 가능성) 바로 다음 배치를, 아니면 잠시 쉬고 재폴링
        await asyncio.sleep(0 if dispatched >= BATCH_SIZE else POLL_INTERVAL_SECONDS)
