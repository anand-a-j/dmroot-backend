from typing import Any


def success_response(data: Any = None, message: str = "Request successful") -> dict:
    return {
        "success": True,
        "message": message,
        "data": data,
    }


def error_response(
    message: str,
    code: str = "INTERNAL_SERVER_ERROR",
    details: Any = None,
    request_id: str | None = None,
) -> dict:
    return {
        "success": False,
        "message": message,
        "error": {
            "code": code,
            "details": details,
        },
        "request_id": request_id,
    }
