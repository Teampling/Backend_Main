from enum import Enum


class WorkState(str, Enum):
    PLANNED = "planned"
    DOING = "doing"
    DONE = "done"

class ProviderType(str, Enum):
    LOCAL = "local"
    GOOGLE = "google"
    KAKAO = "kakao"
    NAVER = "naver"

class MemberRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class ChatRoomType(str, Enum):
    GROUP = "group"
    DIRECT = "direct"

class NotificationTargetType(int, Enum):
    """Notification.target_type 컬럼(SmallInteger)에 대응하는 의미. DB에는 int 값 그대로 저장된다."""
    PROJECT = 0
    WORK = 1
    OTHER = 2
    NOTICE = 3
    INVITATION = 4