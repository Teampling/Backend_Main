from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.shared.enums import ChatRoomType
from app.modules.member.schemas import MemberOut

class ChatMessageBase(BaseModel):
    content: str

class ChatMessageCreate(ChatMessageBase):
    chat_room_id: UUID

class ChatMessageRead(ChatMessageBase):
    id: UUID
    chat_room_id: UUID
    sender_id: UUID
    sender: MemberOut
    created_at: datetime

    class Config:
        from_attributes = True

class ChatRoomBase(BaseModel):
    project_id: UUID
    type: ChatRoomType
    name: str | None = None

class ChatRoomCreate(ChatRoomBase):
    pass

class DirectChatRoomCreate(BaseModel):
    target_member_id: UUID

class ChatRoomRead(ChatRoomBase):
    id: UUID
    created_at: datetime
    members: list[MemberOut] = []
    
    class Config:
        from_attributes = True

class ChatRoomDetailRead(ChatRoomRead):
    members: list[MemberOut]
    # messages: list[ChatMessageRead] # 메시지는 별도 페이징 API로 가져오는 것이 효율적
