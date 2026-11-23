import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from app.api.router import api_router
from app.core.config import settings
from app.core.database import close_pool, init_pool
from app.core.exception_handlers import (
    app_exception_handler,
    http_exception_handler,
    unexpected_exception_handler,
    validation_exception_handler,
)
from app.core.exceptions import AppException
from app.core.logging import setup_logging
from app.middleware.request_logging import request_logging_middleware

setup_logging(settings.app_env)
logger = logging.getLogger(__name__)

is_production = settings.app_env == "production"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup: open the database pool. Shutdown: close it cleanly.
    await init_pool()
    logger.info("%s started (env=%s)", settings.app_name, settings.app_env)
    yield
    await close_pool()
    logger.info("%s stopped", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
    # Hide interactive API docs in production
    docs_url=None if is_production else "/docs",
    redoc_url=None,
    openapi_url=None if is_production else "/openapi.json",
)


# Error handlers: every error returns the same JSON shape
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unexpected_exception_handler)


# Middleware: request id + request loggging
app.middleware("http")(request_logging_middleware)


app.include_router(api_router)











# from fastapi import FastAPI
# from fastapi.exceptions import RequestValidationError
# from starlette.exceptions import HTTPException as StarletteHTTPException

# # # Replace with your actual settings import.
# # from app.core.config import settings
# from app.core.exception_handlers import (
#     app_exception_handler,
#     http_exception_handler,
#     unexpected_exception_handler,
#     validation_exception_handler,
# )
# from app.core.exceptions import AppException
# from app.core.logging import setup_logging
# from app.middleware import request_logging_middleware

# # setup_logging(settings.ENVIRONMENT)

# # app = FastAPI(
# #     title="DMRoot API",
# #     debug=settings.DEBUG,
# # )

# # Register exception handlers.
# app.add_exception_handler(
#     AppException,
#     app_exception_handler,
# )

# app.add_exception_handler(
#     StarletteHTTPException,
#     http_exception_handler,
# )

# app.add_exception_handler(
#     RequestValidationError,
#     validation_exception_handler,
# )

# app.add_exception_handler(
#     Exception,
#     unexpected_exception_handler,
# )

# # Register middleware.
# app.middleware("http")(request_logging_middleware)


# @app.get("/health")
# async def health():
#     return {"status": "ok"}



"""Application entry point: startup/shutdown, error handlers, middleware.

Routers are added in a later stage, once the first module router exists.
"""

# from collections.abc import AsyncIterator
# from contextlib import asynccontextmanager
# import logging

# from fastapi import FastAPI
# from fastapi.exceptions import RequestValidationError
# from starlette.exceptions import HTTPException

# from app.core.config import settings
# from app.core.database import close_pool, init_pool
# from app.core.exception_handlers import (
#     app_exception_handler,
#     http_exception_handler,
#     unexpected_exception_handler,
#     validation_exception_handler,
# )
# from app.core.exceptions import AppException
# from app.core.logging import setup_logging
# from app.middleware.request_logging import request_logging_middleware

# setup_logging(settings.app_env)
# logger = logging.getLogger(__name__)

# is_production = settings.app_env == "production"


# @asynccontextmanager
# async def lifespan(app: FastAPI) -> AsyncIterator[None]:
#     await init_pool()
#     logger.info("%s started (env=%s)", settings.app_name, settings.app_env)
#     yield
#     await close_pool()
#     logger.info("%s stopped", settings.app_name)


# app = FastAPI(
#     title=settings.app_name,
#     debug=settings.debug,
#     lifespan=lifespan,
#     # Hide interactive API docs in production
#     docs_url=None if is_production else "/docs",
#     redoc_url=None,
#     openapi_url=None if is_production else "/openapi.json",
# )

# app.add_exception_handler(AppException, app_exception_handler)
# app.add_exception_handler(HTTPException, http_exception_handler)
# app.add_exception_handler(RequestValidationError, validation_exception_handler)
# app.add_exception_handler(Exception, unexpected_exception_handler)

# app.middleware("http")(request_logging_middleware)

# # Stage 3+: app.include_router(api_router, prefix=settings.api_prefix)


# api_router = APIRouter()
# api_router.include_router(api_router_v1, prefix=settings.api_prefix)

# In main.py, replace the commented last line with:

# python
# from app.api.router import api_router  # (put with the other imports)

# app.include_router(api_router)
