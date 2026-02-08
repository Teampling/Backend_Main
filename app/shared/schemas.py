from typing import TypeVar, Optional, Generic

from pydantic import BaseModel

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    code: str = "OK"
    message: str = "ok"
    data: Optional[T] = None