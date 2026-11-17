"""Data models for session tracking, state machine, and history."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SessionStatus(StrEnum):
    """Lifecycle status of a troubleshooting session."""

    IDLE = "IDLE"
    ACTIVE = "ACTIVE"
    SOLVED = "SOLVED"
    REVEALED = "REVEALED"
    ABANDONED = "ABANDONED"


class ActiveSessionState(BaseModel):
    """Runtime state of an in-progress candidate session."""

    session_id: int = Field(description="Database primary key for this session")
    fault_id: str = Field(description="Active fault catalog ID (e.g. T3)")
    level: int = Field(description="Fault difficulty level (1..5)")
    status: SessionStatus = Field(default=SessionStatus.ACTIVE)
    started_at: str = Field(description="ISO 8601 UTC start timestamp")
    hint_level: int = Field(default=0, description="Highest hint level revealed so far (0..3)")
    failed_submits: int = Field(
        default=0, description="Number of unsuccessful verification attempts"
    )
    no_ai: bool = Field(default=False, description="Whether session runs without AI assistance")


class SessionRecord(BaseModel):
    """Archived troubleshooting session summary from SQLite store."""

    id: int
    fault_id: str
    level: int
    started_at: str
    finished_at: str | None = None
    status: str
    hints_used: int
    failed_submits: int
    explanation: str | None = None
    tech_score: int | None = None
    ai_score: int | None = None
    final_score: int | None = None
    seconds: int | None = None
    extra_data: dict[str, Any] = Field(default_factory=dict)
