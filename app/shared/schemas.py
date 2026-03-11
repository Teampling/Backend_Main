from typing import TypeVar, Optional, Generic

from pydantic import BaseModel

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    code: str = "OK"
    message: str = "ok"
    data: Optional[T] = None

    @classmethod
    def success(cls, data: T, message: str = "ok", code: str = "OK"):
        return cls(code=code, message=message, data=data)

    @classmethod
    def fail(cls, message: str = "error", code: str = "ERROR"):
        return cls(code=code, message=message, data=None)

class PageOut(BaseModel, Generic[T]):
    items: list[T]
    page: int
    size: int
    total: int