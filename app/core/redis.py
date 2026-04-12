import redis.asyncio as redis
from app.core.config import settings

# Redis 클라이언트 설정
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    db=settings.REDIS_DB,
    decode_responses=True # 결과를 문자열로 받기 위해
)

async def get_redis():
    """
    FastAPI 의존성 주입을 위한 redis 클라이언트 반환 함수
    """
    return redis_client
