from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pyexpat.errors import messages
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.shared.schemas import ApiResponse

#오류가 터졌을 때 자동으로 API 응답 형태에 맞춰서 응답을 할 수 있게 해주는 handler
#사용자 요청 -> 라우터 -> handler(자동으로 요청을 처리) -> 서비스 -> 레포지토리 -> DB
def register_exception_handlers(app: FastAPI):

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        if isinstance(exc.detail, dict):
            code = exc.detail.get("code", "HTTP_ERROR")
            message = exc.detail.get("message", "Error")
            data = exc.detail.get("data")

        else:
            if exc.status_code ==401:
                code = "UNAUTHORIZED"
            elif exc.status_code == 403:
                code = "FORBIDDEN"
            elif exc.status_code == 404:
                code = "NOT_FOUND"
            else:
                code = "HTTP_ERROR"
            message = str(exc.detail)
            data = None

        body = ApiResponse(
            code=code,
            message=message,
            data=data,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=body.model_dump(),
        )


    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        body = ApiResponse(
            code="VALIDATION_ERROR",
            message="Invalid request",
            data=exc.errors(),
        )

        return JSONResponse(
            status_code=422,
            content=body.model_dump(),
        )