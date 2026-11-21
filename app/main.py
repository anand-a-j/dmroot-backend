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
