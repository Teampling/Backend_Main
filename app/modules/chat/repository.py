from sqlalchemy.orm import selectinload
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, and_, func
from app.modules.chat.models import ChatRoom, ChatRoomMember, ChatMessage
from app.shared.enums import ChatRoomType

class ChatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_room_by_id(self, room_id: UUID) -> ChatRoom | None:
        stmt = (
            select(ChatRoom)
            .where(ChatRoom.id == room_id, ChatRoom.is_deleted == False)
            .options(selectinload(ChatRoom.members))
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def get_rooms_by_project(self, project_id: UUID, member_id: UUID) -> list[ChatRoom]:
        """
        특정 프로젝트 내에서 해당 멤버가 속한 채팅방 목록을 조회합니다.
        """
        stmt = (
            select(ChatRoom)
            .join(ChatRoomMember)
            .where(
                ChatRoom.project_id == project_id,
                ChatRoomMember.member_id == member_id,
                ChatRoom.is_deleted == False
            )
            .options(selectinload(ChatRoom.members))
            .order_by(ChatRoom.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_direct_room(self, project_id: UUID, member_a: UUID, member_b: UUID) -> ChatRoom | None:
        """
        프로젝트 내 두 멤버 간의 1:1 채팅방이 이미 존재하는지 확인합니다.
        """
        # 두 멤버가 모두 포함된 1:1 채팅방 조회
        stmt = (
            select(ChatRoom)
            .where(
                ChatRoom.project_id == project_id,
                ChatRoom.type == ChatRoomType.DIRECT,
                ChatRoom.is_deleted == False
            )
            .join(ChatRoomMember)
            .where(ChatRoomMember.member_id.in_([member_a, member_b]))
            .options(selectinload(ChatRoom.members))
            .group_by(ChatRoom.id)
            .having(func.count(ChatRoomMember.member_id) == 2)
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def get_group_room(self, project_id: UUID) -> ChatRoom | None:
        """
        프로젝트의 단체 채팅방을 조회합니다.
        """
        stmt = (
            select(ChatRoom)
            .where(
                ChatRoom.project_id == project_id,
                ChatRoom.type == ChatRoomType.GROUP,
                ChatRoom.is_deleted == False
            )
            .options(selectinload(ChatRoom.members))
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def save_room(self, room: ChatRoom) -> ChatRoom:
        self.session.add(room)
        await self.session.flush()
        return room

    async def add_member_to_room(self, room_id: UUID, member_id: UUID):
        member = ChatRoomMember(chat_room_id=room_id, member_id=member_id)
        self.session.add(member)
        await self.session.flush()

    async def save_message(self, message: ChatMessage) -> ChatMessage:
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message, ["sender"])
        return message

    async def get_messages(self, room_id: UUID, limit: int = 50, offset: int = 0) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.chat_room_id == room_id, ChatMessage.is_deleted == False)
            .options(selectinload(ChatMessage.sender))
            .order_by(ChatMessage.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def is_room_member(self, room_id: UUID, member_id: UUID) -> bool:
        stmt = select(ChatRoomMember).where(
            ChatRoomMember.chat_room_id == room_id,
            ChatRoomMember.member_id == member_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() is not None

    async def delete_room(self, room: ChatRoom) -> None:
        """채팅방을 소프트 삭제합니다."""
        room.is_deleted = True
        room.deleted_at = datetime.now(timezone.utc)
        self.session.add(room)
        await self.session.flush()
