"""Unit tests for logging and redaction."""

import json
import logging
from pathlib import Path

from t2t.logging_setup import JsonFormatter, RedactingFilter, setup_logging


def test_redacting_filter() -> None:
    """Verify redacting filter masks sensitive words."""
    redactor = RedactingFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Connecting with password: MySecretPassword123!",
        args=(),
        exc_info=None,
    )
    redactor.filter(record)
    assert "MySecretPassword123!" not in record.msg
    assert "***" in record.msg


def test_json_formatter() -> None:
    """Verify JsonFormatter outputs valid JSON."""
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.WARNING,
        pathname="",
        lineno=0,
        msg="Warning message",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    data = json.loads(formatted)
    assert data["level"] == "WARNING"
    assert data["message"] == "Warning message"


def test_setup_logging(tmp_path: Path) -> None:
    """Verify setup_logging configures file handler."""
    log_file = tmp_path / "logs" / "test.log"
    logger = setup_logging(log_file=log_file, level=logging.DEBUG)
    logger.info("Test message with secret=SuperSecret")
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Test message" in content
    assert "SuperSecret" not in content
