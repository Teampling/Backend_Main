from fastapi import FastAPI
from pydantic import BaseModel, Field, ConfigDict
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logger import setup_logging
from app.core.middleware import RequestIdMiddleware
from app.shared.schemas import ApiResponse

class HealthOut(BaseModel):
    status: str = Field(example="ok")
    app: str = Field(example="teampling-api")
    env: str = Field(example="dev")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"status": "ok", "app": "teampling-api", "env": "dev"}
        }
    )

def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title=settings.APP_NAME)

    # Middleware
    app.add_middleware(RequestIdMiddleware)

    # CORS
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Exception handler
    @app.exception_handler(AppError)
    async def app_error_handler(_, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    # Routers
    # app.include_router(auth_router)

    @app.get("/health", response_model=ApiResponse[HealthOut])
    def health():
        return ApiResponse(
            data=HealthOut(
                status="ok",
                app=settings.APP_NAME,
                env=settings.APP_ENV,
            ),
            code="HEALTH_OK",
            message="서비스 정상 동작 중",
        )

    return app

app = create_app()