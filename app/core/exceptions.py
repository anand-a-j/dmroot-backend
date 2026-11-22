from typing import Any


class AppException(Exception):
    """Base exception for application-level errors."""

    def __init__(
        self,
        message: str = "Something went wrong",
        code: str = "APPLICATION_ERROR",
        status_code: int = 400,
        details: Any = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details

        super().__init__(message)


class BadRequestException(AppException):
    def __init__(self, message="Bad request", details=None):
        super().__init__(
            message=message,
            code="BAD_REQUEST",
            status_code=400,
            details=details,
        )


class ForbiddenException(AppException):
    def __init__(self, message="You don't have permission"):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=403,
        )


class NotFoundException(AppException):
    def __init__(self, message="Resource not found"):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
        )


class ConflictException(AppException):
    def __init__(self, message="Resource already exists"):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
        )


class RateLimitException(AppException):
    def __init__(self, message="Too many requests"):
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
        )


class ExternalServiceException(AppException):
    def __init__(self, message="External service unavailable"):
        super().__init__(
            message=message,
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
        )


class UnauthorizedException(AppException):
    """401 - missing, invalid or expired credentials."""

    def __init__(
        self, message: str = "Authentication required", details: dict | None = None
    ) -> None:
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=401,
            details=details,
        )
