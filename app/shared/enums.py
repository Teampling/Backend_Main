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

class NotificationEventType(str, Enum):
    # 공지
    NOTICE_CREATED = "notice_created"
    NOTICE_UPDATED = "notice_updated"
    # 작업
    WORK_ASSIGNED = "work_assigned"
    WORK_STATUS_CHANGED = "work_status_changed"
    # 프로젝트
    PROJECT_INVITED = "project_invited"
    PROJECT_MEMBER_JOINED = "project_member_joined"
    PROJECT_INVITATION_DECLINED = "project_invitation_declined"
    PROJECT_MEMBER_REMOVED = "project_member_removed"
    PROJECT_LEADERSHIP_TRANSFERRED = "project_leadership_transferred"
