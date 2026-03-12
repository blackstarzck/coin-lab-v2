from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1)
    total: int = Field(default=0, ge=0)
    has_next: bool


class ApiResponse(BaseModel, Generic[T]):
    success: Literal[True] = True
    data: T | Any = None
    meta: dict[str, object] | None = None
    trace_id: str
    timestamp: str


class ErrorResponse(BaseModel):
    success: Literal[False] = False
    error_code: str
    message: str
    details: dict[str, object] | None = None
    trace_id: str
    timestamp: str
