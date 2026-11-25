import json
import logging
import re
import sys
from datetime import UTC, datetime

_SENSITIVE_PATTERN = re.compile(
    r"""(?ix)
    (["']?(?:access_token|client_secret|authorization|token)["']?)
    (\s*[:=]\s*)                                                     
    (?:Bearer\s+)?["']?[^\s"',;&}\]]+["']?                          
    """
)
_BEARER_PATTERN = re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+")


def redact(text: str) -> str:
    text = _SENSITIVE_PATTERN.sub(r"\1\2[REDACTED]", text)
    return _BEARER_PATTERN.sub("Bearer [REDACTED]", text)


class RedactingFilter(logging.Filter):
    """Scrubs secrets from messages and tracebacks before any formatter sees them."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = ()
        if record.exc_info:
            record.exc_text = redact(
                logging.Formatter().formatException(record.exc_info)
            )
            record.exc_info = None
        return True


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

        exc = record.exc_text or (
            self.formatException(record.exc_info) if record.exc_info else None
        )
        if exc:
            log_data["exception"] = exc

        if hasattr(record, "audit"):
            log_data["audit"] = record.audit

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
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

