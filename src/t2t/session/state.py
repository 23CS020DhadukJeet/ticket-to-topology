"""Persistent state management for active candidate troubleshooting sessions.

Maintains .t2t/state.json with FileLock synchronization.
"""

import json
from pathlib import Path

from filelock import FileLock, Timeout
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from t2t.errors import StateCorrupt, T2TError
from t2t.session.models import ActiveSessionState, SessionStatus

DEFAULT_STATE_FILE = Path(".t2t/state.json")


class StateFileModel(BaseModel):
    """File serialization schema for .t2t/state.json."""

    model_config = ConfigDict(populate_by_name=True)

    active_fault: str | None = None
    session_id: int | None = None
    level: int | None = None
    started_at: str | None = None
    hint_level: int = 0
    failed_submits: int = 0
    no_ai: bool = False
    schema_version: int = Field(default=1, alias="schema", serialization_alias="schema")


def get_session_lock(
    state_file: Path = DEFAULT_STATE_FILE,
    timeout: float = 5.0,
) -> FileLock:
    """Retrieve FileLock for the state file."""
    lock_path = state_file.with_suffix(state_file.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    return FileLock(str(lock_path), timeout=timeout)


def get_active_session(
    state_file: Path = DEFAULT_STATE_FILE,
    lock_timeout: float = 5.0,
) -> ActiveSessionState | None:
    """Read the current active session state from disk under lock.

    Returns None if no session is active.
    """
    if not state_file.is_file():
        return None

    lock = get_session_lock(state_file, timeout=lock_timeout)
    try:
        with lock:
            raw = state_file.read_text(encoding="utf-8").strip()
            if not raw:
                return None
            data = json.loads(raw)
            model = StateFileModel.model_validate(data)
            if not model.active_fault or model.session_id is None:
                return None
            return ActiveSessionState(
                session_id=model.session_id,
                fault_id=model.active_fault,
                level=model.level or 1,
                status=SessionStatus.ACTIVE,
                started_at=model.started_at or "",
                hint_level=model.hint_level,
                failed_submits=model.failed_submits,
                no_ai=model.no_ai,
            )
    except (json.JSONDecodeError, ValidationError) as err:
        raise StateCorrupt(f"Corrupt state file {state_file}: {err}") from err
    except Timeout as err:
        raise T2TError(f"Timed out acquiring session lock for {state_file}") from err


def save_active_session(
    state: ActiveSessionState,
    state_file: Path = DEFAULT_STATE_FILE,
    lock_timeout: float = 5.0,
) -> None:
    """Persist active session state to disk under lock."""
    lock = get_session_lock(state_file, timeout=lock_timeout)
    try:
        with lock:
            state_file.parent.mkdir(parents=True, exist_ok=True)
            model = StateFileModel(
                active_fault=state.fault_id,
                session_id=state.session_id,
                level=state.level,
                started_at=state.started_at,
                hint_level=state.hint_level,
                failed_submits=state.failed_submits,
                no_ai=state.no_ai,
                schema=1,
            )
            state_file.write_text(model.model_dump_json(indent=2), encoding="utf-8")
    except Timeout as err:
        raise T2TError(f"Timed out acquiring session lock for {state_file}") from err


def clear_active_session(state_file: Path = DEFAULT_STATE_FILE) -> None:
    """Clear active session state from disk under lock."""
    lock = get_session_lock(state_file)
    try:
        with lock:
            if state_file.is_file():
                state_file.unlink()
    except Timeout as err:
        raise T2TError(f"Timed out acquiring session lock for {state_file}") from err
