import json
import logging
import sys
from datetime import UTC, datetime


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:

        log_data = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=UTC,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(environment: str = "development"):

    handler = logging.StreamHandler(sys.stdout)

    if environment == "production":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root_logger = logging.getLogger()

    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    root_logger.setLevel(logging.INFO if environment == "production" else logging.DEBUG)

    # Reduce unnecessary third-party logs.
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)


# How to use log
# import logging

# logger = logging.getLogger(__name__)

# logger.info("User registered")
# logger.warning("Instagram token is expiring")
# logger.error("Failed to process automation")