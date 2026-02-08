from sqlalchemy import DateTime, func, Boolean
from sqlalchemy.orm import mapped_column, Mapped


class TimestampMixin:
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

class SoftDeleteMixin:
    is_deleted = Mapped[bool] = mapped_column(
        Boolean,
        server_default="false",
        nullable=False,
    )