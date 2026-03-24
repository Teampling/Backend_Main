from enum import IntEnum, Enum


class WorkState(IntEnum):
    PLANNED = 0
    DOING = 1
    DONE = 2

class ProviderType(str, Enum):
    LOCAL = "local"
    GOOGLE = "google"
    KAKAO = "kakao"
    NAVER = "naver"