from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Enum, Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.shared.models.base import BaseModel
from app.shared.enums import ChatRoomType

if TYPE_CHECKING:
    from app.modules.member.models import Member
    from app.modules.project.models import Project

class ChatRoomMember(SQLModel, table=True):
    __tablename__ = "chat_room_members"

    chat_room_id: UUID = Field(foreign_key="chat_rooms.id", primary_key=True)
    member_id: UUID = Field(foreign_key="members.id", primary_key=True)

    joined_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

class ChatRoom(BaseModel, table=True):
    __tablename__ = "chat_rooms"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    type: ChatRoomType = Field(
        sa_column=Column(
            Enum(ChatRoomType, name="chatroomtype", values_callable=lambda x: [e.value for e in x]),
            nullable=False
        )
    )
    name: str | None = Field(default=None, description="채팅방 이름 (단체 채팅방용)")

    project: "Project" = Relationship()
    members: list["Member"] = Relationship(link_model=ChatRoomMember)
    messages: list["ChatMessage"] = Relationship(
        back_populates="chat_room", 
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "ChatMessage.created_at"}
    )

class ChatMessage(BaseModel, table=True):
    __tablename__ = "chat_messages"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    chat_room_id: UUID = Field(foreign_key="chat_rooms.id", nullable=False)
    sender_id: UUID = Field(foreign_key="members.id", nullable=False)
    content: str = Field(nullable=False)

    chat_room: ChatRoom = Relationship(back_populates="messages")
    sender: "Member" = Relationship()
