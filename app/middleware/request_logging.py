import logging
import time
import uuid

from fastapi import Request

logger = logging.getLogger("dmroot.access")


async def request_logging_middleware(
        request: Request,
        call_next,
):
    request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    start_time = time.perf_counter()

    try:
        response = await call_next(request)

        duration = round(
            (time.perf_counter() - start_time) * 1000,2,

        )

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "HTTP request completed",
            extra={"request_id" : request_id},
            # Keep access metadata out of sensitive request contents.
        )

        logger.info(
             "%s %s %s %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            duration,
            extra={"request_id": request_id},
        )

        return response

    except Exception:
        logger.exception(
            "HTTP request failed",
            extra={"request_id": request_id},
        )
        raise