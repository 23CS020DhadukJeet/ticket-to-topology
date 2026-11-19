"""Logging configuration with sensitive data redaction, rotation, and correlation IDs."""

import contextvars
import json
import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)


def set_correlation_id(correlation_id: str | None) -> None:
    """Set the session correlation ID for the current context."""
    _correlation_id.set(correlation_id)


def get_correlation_id() -> str | None:
    """Get the session correlation ID for the current context."""
    return _correlation_id.get()


class CorrelationFilter(logging.Filter):
    """Filter that injects the current correlation_id into the log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Inject correlation_id into the log record."""
        cid = get_correlation_id()
        record.correlation_id = cid or "-"
        return True


class RedactingFilter(logging.Filter):
    """Filter that masks passwords, keys, and credentials in log records."""

    PATTERNS = [
        re.compile(r"(password|secret|key|token)\s*[:=]\s*([^\s,;]+)", re.IGNORECASE),
        re.compile(
            r"(username\s+\S+\s+(?:privilege\s+\d+\s+)?(?:secret|password)\s+)(\S+)",
            re.IGNORECASE,
        ),
        re.compile(r"\b(sk-[a-zA-Z0-9_\-]{8,})\b"),
        re.compile(r"\b(AIzaSy[a-zA-Z0-9_\-]{8,})\b"),
        re.compile(r"(Bearer\s+)([a-zA-Z0-9_\.\-]{10,})", re.IGNORECASE),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Sanitize record message."""
        try:
            msg = record.getMessage()
            record.args = None
        except Exception:
            msg = str(record.msg)

        for pattern in self.PATTERNS:
            msg = pattern.sub(r"\1 ***", msg) if pattern.groups == 2 else pattern.sub(r"***", msg)
        record.msg = msg
        return True


class JsonFormatter(logging.Formatter):
    """Format log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Return JSON-encoded string for the record."""
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "correlation_id": getattr(record, "correlation_id", "-"),
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def setup_logging(
    log_file: Path = Path("logs/t2t.log"),
    level: int = logging.INFO,
    json_format: bool = False,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Logger:
    """Configure root logger with rotating file handler, redactor, and correlation filter."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("t2t")
    logger.setLevel(level)
    logger.handlers.clear()

    redactor = RedactingFilter()
    corr_filter = CorrelationFilter()

    # Rotating File Handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.addFilter(corr_filter)
    file_handler.addFilter(redactor)

    if json_format:
        file_handler.setFormatter(JsonFormatter())
    else:
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s: %(message)s"
            )
        )

    logger.addHandler(file_handler)
    return logger
