"""AI call sink interface for telemetry and audit logging.

Per Phase 5 design:
Keeps an interface AICallSink for logging provider, model, prompt_version,
latency_ms, ok to be integrated with SQLite in Phase 6.
"""

from typing import Protocol

from pydantic import BaseModel


class AICallRecord(BaseModel):
    """Metadata record for an AI interaction."""

    session_id: int | None = None
    purpose: str
    provider: str
    model: str
    prompt_version: str
    latency_ms: int
    ok: bool
    error: str | None = None


class AICallSink(Protocol):
    """Protocol for logging AI calls."""

    def log_call(self, record: AICallRecord) -> None:
        """Record an AI call invocation."""
        ...


class NullAICallSink:
    """Default no-op sink when logging is not configured."""

    def log_call(self, record: AICallRecord) -> None:
        pass
