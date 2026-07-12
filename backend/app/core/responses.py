from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[T] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    details: Optional[Any] = None


def ok(data: Any = None, message: str = "Operation completed successfully") -> dict:
    return {"success": True, "message": message, "data": data}


def err(message: str, details: Any = None) -> dict:
    return {"success": False, "message": message, "details": details}
