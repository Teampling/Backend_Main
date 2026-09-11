#dto
from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict
from sqlmodel import SQLModel, Field

from app.shared.enums import ChatRoomType
from app.modules.member.schemas import MemberOut


#요청
class DirectChatRoomCreateIn(SQLModel):
    target_member_id: UUID = Field(description="대화 상대 회원 고유키")


#응답
class ChatMessageOut(SQLModel):
    id: UUID = Field(description="메시지 고유키")
    chat_room_id: UUID = Field(description="채팅방 고유키")
    sender_id: UUID = Field(description="발신자 회원 고유키")
    sender: MemberOut = Field(description="발신자 정보")
    content: str = Field(description="메시지 내용")
    created_at: datetime = Field(description="생성 일시")

    model_config = ConfigDict(from_attributes=True)


class ChatRoomOut(SQLModel):
    id: UUID = Field(description="채팅방 고유키")
    project_id: UUID = Field(description="프로젝트 고유키")
    type: ChatRoomType = Field(description="채팅방 유형(group/direct)")
    name: str | None = Field(default=None, description="채팅방 이름 (단체 채팅방용)")
    created_at: datetime = Field(description="생성 일시")
    members: list[MemberOut] = Field(default=[], description="채팅방 참여자 목록")
    unread_count: int = Field(default=0, description="읽지 않은 메시지 수")
    last_message: ChatMessageOut | None = Field(default=None, description="마지막 메시지")

    model_config = ConfigDict(from_attributes=True)
