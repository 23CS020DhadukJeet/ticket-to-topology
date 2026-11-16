"""Persistent state management for active injected fault.

Uses .t2t/state.json with filelock.
NOTE: Per AGENTS.md Hard Rule 3, t2t.faults must never import t2t.ai.
"""

import contextlib
import json
from datetime import UTC, datetime
from pathlib import Path

from filelock import FileLock, Timeout
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from t2t.errors import StateCorrupt, T2TError


class StateModel(BaseModel):
    """Schema for .t2t/state.json."""

    model_config = ConfigDict(populate_by_name=True)

    active_fault: str | None = None
    injected_at: str | None = None
    schema_version: int = Field(default=1, alias="schema", serialization_alias="schema")


DEFAULT_STATE_FILE = Path(".t2t/state.json")


def _get_lock(state_file: Path) -> FileLock:
    lock_path = state_file.with_suffix(state_file.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    return FileLock(str(lock_path), timeout=5.0)


def _read_state_unlocked(state_file: Path) -> StateModel:
    """Read state from disk without acquiring lock (caller must hold lock or ensure safety)."""
    if not state_file.is_file():
        return StateModel()
    raw = state_file.read_text(encoding="utf-8")
    if not raw.strip():
        return StateModel()
    data = json.loads(raw)
    return StateModel.model_validate(data)


def get_state(state_file: Path = DEFAULT_STATE_FILE) -> StateModel:
    """Read current state from state_file under lock.

    Raises:
        StateCorrupt: If the state file contains invalid JSON or invalid schema.
    """
    if not state_file.is_file():
        return StateModel()

    lock = _get_lock(state_file)
    try:
        with lock:
            return _read_state_unlocked(state_file)
    except (json.JSONDecodeError, ValidationError) as err:
        raise StateCorrupt(f"Corrupt state file {state_file}: {err}") from err
    except Timeout as err:
        raise T2TError(f"Timed out acquiring state lock for {state_file}") from err


def set_active_fault(fault_id: str, state_file: Path = DEFAULT_STATE_FILE) -> None:
    """Set active fault ID in state_file under lock.

    Raises:
        T2TError: If another fault is already active.
    """
    lock = _get_lock(state_file)
    try:
        with lock:
            current = _read_state_unlocked(state_file)
            if current.active_fault is not None:
                raise T2TError(
                    f"Another fault is already active: '{current.active_fault}'. "
                    "Run 't2t reset' before injecting a new fault."
                )

            state_file.parent.mkdir(parents=True, exist_ok=True)
            now_iso = datetime.now(UTC).isoformat()
            new_state = StateModel(active_fault=fault_id, injected_at=now_iso, schema=1)
            state_file.write_text(new_state.model_dump_json(indent=2), encoding="utf-8")
    except (json.JSONDecodeError, ValidationError) as err:
        raise StateCorrupt(f"Corrupt state file {state_file}: {err}") from err
    except Timeout as err:
        raise T2TError(f"Timed out acquiring state lock for {state_file}") from err


def clear_active_fault(state_file: Path = DEFAULT_STATE_FILE, force: bool = False) -> None:
    """Clear active fault in state_file under lock.

    If force is True, cleans up existing lock file if stuck.
    """
    lock = _get_lock(state_file)
    try:
        with lock:
            state_file.parent.mkdir(parents=True, exist_ok=True)
            new_state = StateModel(active_fault=None, injected_at=None, schema=1)
            state_file.write_text(new_state.model_dump_json(indent=2), encoding="utf-8")
    except Timeout as err:
        if force:
            # Forcibly release / recreate lock
            lock_path = state_file.with_suffix(state_file.suffix + ".lock")
            with contextlib.suppress(OSError):
                lock_path.unlink(missing_ok=True)
            new_state = StateModel(active_fault=None, injected_at=None, schema=1)
            state_file.write_text(new_state.model_dump_json(indent=2), encoding="utf-8")
        else:
            raise T2TError(f"Timed out acquiring state lock for {state_file}") from err
