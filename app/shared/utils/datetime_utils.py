from datetime import datetime, timezone


def to_utc(dt: datetime | None) -> datetime | None:
    """naive datetime을 UTC-aware로 보정한다.

    UtcDateTime(timezone-aware) 컬럼에 클라이언트가 보낸 tz 없는 datetime을
    그대로 저장하면 'naive datetime is disallowed'로 실패하므로, 저장 전에 보정한다.
    """
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
