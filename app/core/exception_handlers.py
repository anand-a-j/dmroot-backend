import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException
from app.core.responses import error_response

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException):

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            message=exc.message,
            code=exc.code,
            details=exc.details,
            request_id=getattr(request.state, "request_id", None),
        ),
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
):
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            message=str(exc.detail),
            code="HTTP_ERROR",
            request_id=getattr(request.state, "request_id", None),
        ),
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    # Exclude submitted input values to avoid leaking sensitive data.
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]

    return JSONResponse(
        status_code=422,
        content=error_response(
            message="Request validation failed",
            code="VALIDATION_ERROR",
            details=details,
            request_id=getattr(request.state, "request_id", None),
        ),
    )


async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
):
    request_id = getattr(request.state, "request_id", None)

    logger.error(
        "Unhandled application exception",
        exc_info=(type(exc), exc, exc.__traceback__),
        extra={"request_id": request_id},
    )

    return JSONResponse(
        status_code=500,
        content=error_response(
            message="Internal server error",
            code="INTERNAL_SERVER_ERROR",
            request_id=request_id,
        ),
    )
