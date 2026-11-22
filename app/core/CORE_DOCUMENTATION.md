# DMRoot Core Package

## Purpose

`app/core` contains shared application infrastructure:

- environment and application settings
- application-wide constants
- typed application exceptions
- consistent success and error response bodies
- FastAPI exception handlers
- structured and environment-aware logging

The package is designed to keep HTTP, configuration, and error behavior consistent across feature modules.

## File map

| File | Responsibility |
| --- | --- |
| `config.py` | Loads `.env` values and builds the PostgreSQL DSN |
| `constants.py` | Stores shared application limits and defaults |
| `exceptions.py` | Defines application-level exception types |
| `exception_handlers.py` | Converts exceptions and validation failures into JSON responses |
| `responses.py` | Defines standard success and error response dictionaries |
| `logging.py` | Configures root logging and JSON logs for production |
| `__init__.py` | Package marker; currently contains no exports |
| `CORE_DOCUMENTATION.md` | Core package reference |

## Configuration

`config.py` uses Pydantic Settings and loads `.env` from the repository root.

Environment names are case-insensitive. Required values:

- `SECRET_KEY`
- `DB_PASSWORD`

### Application settings

| Environment variable | Field | Default |
| --- | --- | --- |
| `APP_NAME` | `app_name` | `DMRoot` |
| `APP_ENV` | `app_env` | `development` |
| `DEBUG` | `debug` | `false` |
| `API_PREFIX` | `api_prefix` | `/api/v1` |
| `LOG_LEVEL` | `log_level` | `INFO` |

The `app_env` field accepts only `development`, `testing`, or `production`.

### Infrastructure settings

| Environment variable | Field | Default |
| --- | --- | --- |
| `DB_HOST` | `db_host` | `localhost` |
| `DB_PORT` | `db_port` | `5432` |
| `DB_NAME` | `db_name` | `dmroot` |
| `DB_USER` | `db_user` | `postgres` |
| `DB_PASSWORD` | `db_password` | required |
| `REDIS_URL` | `redis_url` | `redis://localhost:6379/0` |
| `CELERY_BROKER_URL` | `celery_broker_url` | `redis://localhost:6379/1` |
| `CELERY_RESULT_BACKEND` | `celery_result_backend` | `redis://localhost:6379/2` |

### Meta settings

| Environment variable | Field | Default |
| --- | --- | --- |
| `META_APP_ID` | `meta_app_id` | empty |
| `META_APP_SECRET` | `meta_app_secret` | `None` |
| `META_WEBHOOK_VERIFY_TOKEN` | `meta_webhook_verify_token` | `None` |
| `META_API_VERSION` | `meta_api_version` | `vXX.X` |

Use the settings singleton:

```python
from app.core.config import settings

database_url = settings.database_dsn
```

The `database_dsn` property URL-encodes the database user and password. The settings instance is cached by `get_setings()`.

> **Naming note:** `get_setings` is currently misspelled. Prefer `settings` for normal use and rename the function to `get_settings` in a future coordinated change.

## Constants

```python
APP_NAME = "DMRoot"
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100
DEFAULT_REQUEST_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
```

Import constants instead of duplicating pagination, timeout, and retry values.

## Exceptions

`AppException` is the base exception and carries:

- `message`: human-readable description
- `code`: stable machine-readable identifier
- `status_code`: HTTP status
- `details`: optional structured context

| Exception | Status | Error code |
| --- | --- | --- |
| `BadRequestException` | 400 | `BAD_REQUEST` |
| `ForbiddenException` | 403 | `FORBIDDEN` |
| `NotFoundException` | 404 | `NOT_FOUND` |
| `ConflictException` | 409 | `CONFLICT` |
| `RateLimitException` | 429 | `RATE_LIMIT_EXCEEDED` |
| `ExternalServiceException` | 502 | `EXTERNAL_SERVICE_ERROR` |

Raise an application exception from service or route code:

```python
from app.core.exceptions import NotFoundException

raise NotFoundException("Automation was not found")
```

Do not raise raw exceptions for expected HTTP failures. Preserve `details` for bad request context only when the data is safe to return.

## Response contracts

### Success

```python
success_response(data, message="Request successful")
```

```json
{
  "success": true,
  "message": "Request successful",
  "data": {}
}
```

### Error

```python
error_response(
    message="Request failed",
    code="BAD_REQUEST",
    details=None,
    request_id=request_id,
)
```

```json
{
  "success": false,
  "message": "Request failed",
  "error": {
    "code": "BAD_REQUEST",
    "details": null
  },
  "request_id": "..."
}
```

Both response helpers return plain dictionaries and do not depend on an ORM or framework response type.

## Exception handling

Register these handlers with FastAPI:

| Handler | Handles |
| --- | --- |
| `app_exception_handler` | `AppException` subclasses |
| `http_exception_handler` | Starlette/FastAPI HTTP exceptions |
| `validation_exception_handler` | Pydantic/FastAPI request validation errors |
| `unexpected_exception_handler` | unhandled application exceptions |

```python
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from app.core.exception_handlers import (
    app_exception_handler,
    http_exception_handler,
    unexpected_exception_handler,
    validation_exception_handler,
)
from app.core.exceptions import AppException

app = FastAPI()

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unexpected_exception_handler)
```

Validation details contain field location, message, and validation type, but submitted values are excluded to avoid secret or payload leakage.

Unexpected exceptions are logged with a traceback and returned as a generic `500` response. The response never exposes the original exception message.

## Logging

Call `setup_logging()` during application startup:

```python
from app.core.config import settings
from app.core.logging import setup_logging

setup_logging(settings.app_env)
```

Behavior:

- development/testing: human-readable text logs
- production: newline-delimited JSON logs
- root log level: `DEBUG` outside production, `INFO` in production
- noisy third-party logs are reduced for `uvicorn.access`, `asyncpg`, and `redis`

JSON log fields:

- `timestamp`
- `level`
- `logger`
- `message`
- `request_id` when present
- `exception` when traceback data exists

## Request tracing integration

`app/middleware/request_logging.py` creates a UUID for each request and stores it in `request.state.request_id`.

It:

1. records elapsed request time
2. adds `X-Request-ID` to the response
3. logs HTTP completion metadata
4. logs failed calls with the request ID

The core exception handlers read the same request ID through `request.state.request_id`.

Suggested middleware setup:

```python
from app.middleware.request_logging import request_logging_middleware

app.middleware("http")(request_logging_middleware)
```

## Optimized usage pattern

Use the core package as follows:

```python
from app.core.config import settings
from app.core.constants import DEFAULT_PAGE_SIZE
from app.core.exceptions import BadRequestException
from app.core.logging import setup_logging
from app.core.responses import success_response

setup_logging(settings.app_env)


async def create_item(payload):
    if not payload:
        raise BadRequestException(
            "Payload is required",
            details={"field": "payload"},
        )

    return success_response(
        data={"page_size": DEFAULT_PAGE_SIZE},
        message="Item created",
    )
```

## Current integration status

- `config.py` is active and used by the database migration runner.
- `exceptions.py`, `responses.py`, `exception_handlers.py`, and `logging.py` are ready to use.
- `app/main.py` contains commented FastAPI bootstrap code and has not yet activated these components.
- `app/core/__init__.py` and `app/middleware/__init__.py` are empty.
- `CORE_DOCUMENTATION.md` documents the implementation as it exists; it should be updated when core APIs change.
