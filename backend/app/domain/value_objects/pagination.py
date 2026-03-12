from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PaginationParams:
    page: int = 1
    page_size: int = 20


@dataclass(slots=True)
class PaginationMeta:
    page: int
    page_size: int
    total: int
    has_next: bool
