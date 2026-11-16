"""Logging configuration with sensitive data redaction."""

import json
import logging
import re
from pathlib import Path
from typing import Any


class RedactingFilter(logging.Filter):
    """Filter that masks passwords, keys, and credentials in log records."""

    PATTERNS = [
        re.compile(r"(password|secret|key|token)\s*[:=]\s*([^\s,;]+)", re.IGNORECASE),
        re.compile(
            r"(username\s+\S+\s+(?:privilege\s+\d+\s+)?(?:secret|password)\s+)(\S+)", re.IGNORECASE
        ),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Sanitize record message."""
        if isinstance(record.msg, str):
            for pattern in self.PATTERNS:
                record.msg = pattern.sub(r"\1 ***", record.msg)
        return True


class JsonFormatter(logging.Formatter):
    """Format log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Return JSON-encoded string for the record."""
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
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
) -> logging.Logger:
    """Configure root logger with file and console handlers and redactor."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("t2t")
    logger.setLevel(level)
    logger.handlers.clear()

    redactor = RedactingFilter()

    # File Handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.addFilter(redactor)

    if json_format:
        file_handler.setFormatter(JsonFormatter())
    else:
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

    logger.addHandler(file_handler)
    return logger
