from pydantic import AwareDatetime
from sqlalchemy_utc import UtcDateTime
from sqlmodel import SQLModel, Field, func


class BaseModel(SQLModel):
    created_at: AwareDatetime = Field(
        default=None,
        nullable=False,
        sa_type=UtcDateTime,
        # 밑에거는 DB 레벨에서 기본값을 정의하기 위한 부분 (기본값을 정의해줘야 하는 컬럼은 이 과정 필요)
        sa_column_kwargs={
            "server_default": func.now(),
        },
    )
    updated_at: AwareDatetime = Field(
        default=None,
        nullable=False,
        sa_type=UtcDateTime,
        sa_column_kwargs={
            "server_default": func.now(),
            "onupdate": func.now(), #datetime.now 대신 func.now() 권장
        },
    )
    is_deleted: bool = Field(
        default=False,
        nullable=False,
        sa_column_kwargs={
            "server_default": "false"
        },
    )
    deleted_at: AwareDatetime = Field(
        default=None,
        nullable=True,
        sa_type=UtcDateTime,
    )