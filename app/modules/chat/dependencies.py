from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.chat.repository import ChatRepository
from app.modules.chat.service import ChatService

async def get_chat_repository(session: AsyncSession = Depends(get_session)) -> ChatRepository:
    return ChatRepository(session)

async def get_chat_service(
    session: AsyncSession = Depends(get_session),
    repository: ChatRepository = Depends(get_chat_repository)
) -> ChatService:
    return ChatService(session, repository)
