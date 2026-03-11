from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.shared.schemas import ApiResponse


def register_exception_handlers(app: FastAPI):

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        if isinstance(exc.detail, dict):
            body = ApiResponse(
                code=exc.detail.get("code", "HTTP_ERROR"),
                message=exc.detail.get("message", "Error"),
                data=None,
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