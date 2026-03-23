from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse


@dataclass
class AppError(Exception):
    """Base application error with HTTP mapping.

    Contract:
      - Inputs: message, code, status_code, details
      - Output: raise to be converted to JSON error response at API boundary
    """

    message: str
    code: str = "app_error"
    status_code: int = 400
    details: dict | None = None


class NotFoundError(AppError):
    def __init__(self, message: str = "Not found", details: dict | None = None) -> None:
        super().__init__(message=message, code="not_found", status_code=404, details=details)


class ConflictError(AppError):
    def __init__(
        self, message: str = "Conflict", details: dict | None = None
    ) -> None:
        super().__init__(message=message, code="conflict", status_code=409, details=details)


class ForbiddenError(AppError):
    def __init__(
        self, message: str = "Forbidden", details: dict | None = None
    ) -> None:
        super().__init__(message=message, code="forbidden", status_code=403, details=details)


class UnauthorizedError(AppError):
    def __init__(
        self, message: str = "Unauthorized", details: dict | None = None
    ) -> None:
        super().__init__(message=message, code="unauthorized", status_code=401, details=details)


# PUBLIC_INTERFACE
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    """Convert AppError to a JSON API response."""
    payload = {"error": {"code": exc.code, "message": exc.message, "details": exc.details}}
    return JSONResponse(status_code=exc.status_code, content=payload)
