from __future__ import annotations

from app.core import error_codes


class AppError(Exception):
    def __init__(self, error_code: str, message: str, details: dict[str, object] | None = None, status_code: int | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.status_code = status_code if status_code is not None else error_codes.status_code_for_error(error_code)


class NotFoundError(AppError):
    def __init__(self, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(error_codes.REQ_NOT_FOUND, message, details, 404)


class ValidationError(AppError):
    def __init__(self, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(error_codes.REQ_INVALID_PAYLOAD, message, details, 400)


class ConflictError(AppError):
    def __init__(self, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(error_codes.REQ_CONFLICT, message, details, 409)


CoinLabError = AppError
