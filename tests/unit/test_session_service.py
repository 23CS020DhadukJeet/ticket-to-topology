"""Unit tests for Phase 6 Session State Machine and Service (U6.2, U6.6, U6.7)."""

from pathlib import Path

import pytest
from filelock import FileLock

from t2t.clock import FakeClock
from t2t.config import Inventory, Router, Settings
from t2t.errors import T2TError
from t2t.session.models import SessionStatus
from t2t.session.service import SessionService
from t2t.session.store import SQLiteStore


@pytest.fixture
def test_env(tmp_path: Path):
    """Set up temporary test environment for SessionService."""
    state_file = tmp_path / "state.json"
    db_file = tmp_path / "t2t.db"
    fixtures_dir = tmp_path / "fixtures"

    # Minimal fixtures for R1, R2, R3, R4 baseline
    for r in ["R1", "R2", "R3", "R4"]:
        r_dir = fixtures_dir / "baseline" / r
        r_dir.mkdir(parents=True)
        (r_dir / "show_version.txt").write_text("Cisco IOS XE Version 17.3\n", encoding="utf-8")
        (r_dir / "show_running_config.txt").write_text(
            f"hostname {r}\nrouter eigrp 100\n network 10.10.1.0 0.0.0.255\n",
            encoding="utf-8",
        )

    inventory = Inventory(
        routers=[
            Router(name="R1", host="192.168.100.11", role="branch"),
            Router(name="R2", host="192.168.100.12", role="core"),
            Router(name="R3", host="192.168.100.13", role="core"),
            Router(name="R4", host="192.168.100.14", role="hq"),
        ]
    )
    settings = Settings(t2t_ai_provider="none")
    store = SQLiteStore(db_file)
    clock = FakeClock(1000.0)

    service = SessionService(
        settings=settings,
        inventory=inventory,
        replay=True,
        clock=clock,
        store=store,
        state_file=state_file,
        fixtures_root=fixtures_dir,
    )
    return service, tmp_path, store, clock


def test_u6_2_illegal_transitions_from_idle(test_env) -> None:
    """When no ticket is active (IDLE), hint/submit/reveal/abandon raise friendly T2TError."""
    service, _, _, _ = test_env

    assert service.get_active_state() is None

    with pytest.raises(T2TError, match="No active ticket session"):
        service.get_hint()

    with pytest.raises(T2TError, match="No active ticket session"):
        service.submit_explanation("Root cause explanation")

    with pytest.raises(T2TError, match="No active ticket session"):
        service.reveal_fault()

    with pytest.raises(T2TError, match="No active ticket session"):
        service.abandon_session()


def test_u6_2_legal_transition_to_active_and_blocked_second_ticket(test_env) -> None:
    """Starting a ticket transitions from IDLE to ACTIVE; second ticket is blocked."""
    service, _, _, _ = test_env

    # 1. Start ticket T3
    state, ticket_text = service.start_ticket(fault_id="T3", no_ai=True)
    assert state.status == SessionStatus.ACTIVE
    assert state.fault_id == "T3"
    assert state.hint_level == 0
    assert state.failed_submits == 0
    assert "vendor" in ticket_text.lower()

    # 2. Starting another ticket while ACTIVE must raise T2TError
    with pytest.raises(T2TError, match="A ticket session for fault 'T3' is already active"):
        service.start_ticket(fault_id="T1")


def test_u6_2_hint_progression_and_capping(test_env) -> None:
    """Requesting hints increments hint_level up to 3 and caps with is_max flag."""
    service, _, _, _ = test_env
    service.start_ticket(fault_id="T3", no_ai=True)

    # Hint 1
    lvl1, text1, penalty1, is_max1 = service.get_hint()
    assert lvl1 == 1
    assert penalty1 == 5
    assert not is_max1

    # Hint 2
    lvl2, text2, penalty2, is_max2 = service.get_hint()
    assert lvl2 == 2
    assert penalty2 == 10
    assert not is_max2

    # Hint 3
    lvl3, text3, penalty3, is_max3 = service.get_hint()
    assert lvl3 == 3
    assert penalty3 == 15
    assert is_max3

    # Hint 4 (Repeats hint 3, capped at 3)
    lvl4, text4, penalty4, is_max4 = service.get_hint()
    assert lvl4 == 3
    assert penalty4 == 15
    assert is_max4
    assert text4 == text3


def test_u6_6_reveal_scores_zero_and_returns_to_idle(test_env) -> None:
    """Revealing an active fault reveals reference fix, sets score 0, and restores IDLE."""
    service, _, store, _ = test_env
    service.start_ticket(fault_id="T3", no_ai=True)

    root_cause, revert_cmds, score = service.reveal_fault()
    assert "R3" in revert_cmds
    assert score.revealed is True
    assert score.total_score == 0

    # Service should be back to IDLE
    assert service.get_active_state() is None

    # History should record REVEALED
    history = store.get_history()
    assert len(history) == 1
    assert history[0]["status"] == "REVEALED"
    assert history[0]["final_score"] == 0


def test_u6_6_abandon_session_restores_idle(test_env) -> None:
    """Abandoning an active fault closes session with ABANDONED and restores IDLE."""
    service, _, store, _ = test_env
    service.start_ticket(fault_id="T3", no_ai=True)

    service.abandon_session()

    assert service.get_active_state() is None
    history = store.get_history()
    assert len(history) == 1
    assert history[0]["status"] == "ABANDONED"


def test_u6_7_file_lock_prevents_concurrent_new_ticket(test_env) -> None:
    """Held lock prevents a second ticket from being injected."""
    service, tmp_path, _, _ = test_env
    service.lock_timeout = 0.2
    lock_file = tmp_path / "state.json.lock"
    external_lock = FileLock(str(lock_file))

    with external_lock, pytest.raises(T2TError, match="lock"):
        service.start_ticket(fault_id="T3", no_ai=True)
