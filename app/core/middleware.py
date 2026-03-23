import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("request")

#API가 호출되면 자동으로 서버에 로그를 찍어주는 함수
class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start = time.time()
        response: Response = await call_next(request)
        elapsed_ms = int((time.time() - start) * 1000)

        response.headers["x-request-id"] = request_id
        logger.info("%s %s %s %dms", request.method, request.url.path, response.status_code, elapsed_ms)
        return response