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