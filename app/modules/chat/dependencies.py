from typing import Annotated

from fastapi import Depends

from app.core.database import DbSessionDep
from app.modules.chat.repository import ChatRepository
from app.modules.chat.service import ChatService
from app.modules.project.repository import ProjectRepository


def get_chat_service(session: DbSessionDep) -> ChatService:
    repository = ChatRepository(session)
    return ChatService(session, repository)

ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
