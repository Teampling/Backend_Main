import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, FileResponse

from app.core.config import settings
from app.core.exception_handler import register_exception_handlers
from app.core.exceptions import AppError
from app.core.logger import setup_logging
from app.core.middleware import RequestIdMiddleware
from app.shared.schemas import ApiResponse
from app.modules.skill.router import router as skill_router
from app.modules.member.router import router as member_router
from app.modules.project.router import router as project_router
from app.modules.work.router import work_router, project_work_router
from app.modules.notice.router import router as notice_router
from app.modules.chat.router import router as chat_router
from app.modules.notification.router import router as notification_router
from app.modules.notification.outbox_relay import run_outbox_relay
from app.modules.notification.consumer import run_notification_consumer
from app.modules.skill.models import Skill
from app.modules.member.models import Member
from app.modules.favorite.models import Favorite
from app.modules.notice.models import Notice
from app.modules.notification.models import Notification, NotificationRecipient, OutboxEvent
from app.modules.project.models import Project
from app.modules.resource.models import Resource
from app.modules.work.models import Work
from app.modules.chat.models import ChatRoom, ChatRoomMember, ChatMessage

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 알림 이벤트 파이프라인: Outbox 릴레이(Postgres -> Redis Stream)와
    # 알림 컨슈머(Redis Stream -> Notification 생성 + 실시간 push)를 백그라운드로 계속 돌린다.
    relay_task = asyncio.create_task(run_outbox_relay())
    consumer_task = asyncio.create_task(run_notification_consumer())

    yield

    for task in (relay_task, consumer_task):
        task.cancel()
    await asyncio.gather(relay_task, consumer_task, return_exceptions=True)

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
    app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

    # Exception Handler 등록
    register_exception_handlers(app)

    # Router 등록
    app.include_router(skill_router)
    app.include_router(member_router)
    app.include_router(project_router)
    app.include_router(work_router)
    app.include_router(project_work_router)
    app.include_router(notice_router)
    app.include_router(chat_router)
    app.include_router(notification_router)

    # Static Files
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    @app.get("/")
    async def read_index():
        return FileResponse("app/static/index.html")

    @app.get("/{page}.html")
    async def read_html(page: str):
        return FileResponse(f"app/static/{page}.html")

    @app.get("/project/invite/accept")
    async def invite_accept_page():
        return FileResponse("app/static/invite-accept.html")

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