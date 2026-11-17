"""Troubleshooting session service coordinating devices, verification, AI, and persistence.

Per BUILD_GUIDE Phase 6:
Coordinates the learner workflow:
new-ticket -> hint -> submit -> reveal -> abandon.
Maintains state machine transitions, lock synchronization, and scoring.
"""

import time
from datetime import UTC, datetime
from pathlib import Path

from t2t.ai.factory import get_provider
from t2t.ai.grader import grade_explanation
from t2t.ai.mentor import generate_hint
from t2t.ai.ticket import generate_ticket, get_deterministic_ticket_fallback
from t2t.clock import Clock, FakeClock, SystemClock
from t2t.config import Inventory, Settings
from t2t.devices.session import DeviceSession
from t2t.errors import T2TError
from t2t.faults.engine import FaultEngine
from t2t.faults.loader import FaultModel, load_catalog, load_fault
from t2t.models import CheckResult
from t2t.session.drift import DriftReport, check_drift
from t2t.session.models import ActiveSessionState
from t2t.session.scoring import ScoreBreakdown, compute_score, get_par_seconds
from t2t.session.state import (
    DEFAULT_STATE_FILE,
    clear_active_session,
    get_active_session,
    save_active_session,
)
from t2t.session.store import SQLiteStore
from t2t.verify.engine import run_all


class SessionService:
    """Service governing troubleshooting session lifecycle and state transitions."""

    def __init__(
        self,
        settings: Settings,
        inventory: Inventory,
        replay: bool = False,
        clock: Clock | None = None,
        store: SQLiteStore | None = None,
        state_file: Path = DEFAULT_STATE_FILE,
        fixtures_root: Path | None = None,
        lock_timeout: float = 5.0,
    ) -> None:
        self.settings = settings
        self.inventory = inventory
        self.replay = replay
        if clock is not None:
            self.clock = clock
        elif replay:
            self.clock = FakeClock(start_time=time.time())
        else:
            self.clock = SystemClock()
        self.store = store or SQLiteStore()
        self.state_file = state_file
        self.fixtures_root: Path = (
            fixtures_root if fixtures_root is not None else Path("tests/fixtures")
        )
        self.lock_timeout = lock_timeout

    def _create_device_session(self) -> DeviceSession:
        """Create a new DeviceSession for network operations."""
        active = self.get_active_state()
        scenario = f"faulted/{active.fault_id}" if active else "baseline"
        return DeviceSession(
            inventory=self.inventory,
            replay=self.replay,
            scenario=scenario,
            clock=self.clock,
            fixtures_root=self.fixtures_root,
        )

    def _create_fault_engine(self, session: DeviceSession) -> FaultEngine:
        """Create a FaultEngine bound to an active DeviceSession."""
        return FaultEngine(
            session=session,
            clock=self.clock,
            inventory=self.inventory,
            state_file=self.state_file,
        )

    def get_active_state(self) -> ActiveSessionState | None:
        """Retrieve current active session, or None if in IDLE state."""
        return get_active_session(self.state_file, lock_timeout=self.lock_timeout)

    def _require_active_state(self) -> ActiveSessionState:
        """Assert that a session is currently ACTIVE, raising a friendly error if IDLE."""
        state = self.get_active_state()
        if state is None:
            raise T2TError("No active ticket session. Run 't2t new-ticket' to start one.")
        return state

    def _load_fault(self, fault_id: str) -> FaultModel:
        """Load fault model from catalog."""
        path = Path(f"src/t2t/faults/catalog/{fault_id}.yaml")
        if not path.is_file():
            raise T2TError(f"Fault catalog entry '{fault_id}' not found.")
        return load_fault(path, self.inventory)

    def start_ticket(
        self,
        fault_id: str | None = None,
        level: int | None = None,
        random_fault: bool = False,
        no_ai: bool = False,
    ) -> tuple[ActiveSessionState, str]:
        """Start a new candidate troubleshooting session.

        Transitions: IDLE -> ACTIVE.
        """
        existing = self.get_active_state()
        if existing is not None:
            raise T2TError(
                f"A ticket session for fault '{existing.fault_id}' is already active. "
                "Run 't2t submit', 't2t reveal', or 't2t abandon' first."
            )

        # 1. Resolve fault to inject
        catalog_dir = Path("src/t2t/faults/catalog")
        catalog = load_catalog(catalog_dir, self.inventory)
        if not catalog:
            raise T2TError("No faults found in catalog.")

        selected_fault: FaultModel
        if fault_id:
            selected_fault = self._load_fault(fault_id)
        elif level is not None:
            matches = [f for f in catalog.values() if f.level == level]
            if not matches:
                raise T2TError(f"No faults found matching level {level}.")
            selected_fault = matches[0]
        elif random_fault:
            selected_fault = list(catalog.values())[0]
        else:
            selected_fault = catalog.get("T3", list(catalog.values())[0])

        # 2. Inject fault on devices
        with self._create_device_session() as session:
            engine = self._create_fault_engine(session)
            engine.inject(selected_fault, skip_baseline_check=True)

        # 3. Create session record in database
        now_dt = datetime.fromtimestamp(self.clock.now(), tz=UTC)
        now_iso = now_dt.isoformat()
        session_id = self.store.create_session(
            fault_id=selected_fault.id,
            level=selected_fault.level,
            started_at=now_iso,
        )
        self.store.set_active_session_id(session_id)

        # 4. Generate incident ticket
        if no_ai or self.settings.t2t_ai_provider == "none":
            ticket_text = get_deterministic_ticket_fallback(
                business_context=selected_fault.business_context,
                symptom_class=selected_fault.symptom_class,
            )
        else:
            provider = get_provider(self.settings, self.clock)
            ticket_text = generate_ticket(
                fault=selected_fault,
                provider=provider,
                sink=self.store,
            )

        # 5. Persist active state to .t2t/state.json
        state = ActiveSessionState(
            session_id=session_id,
            fault_id=selected_fault.id,
            level=selected_fault.level,
            started_at=now_iso,
            hint_level=0,
            failed_submits=0,
            no_ai=no_ai,
        )
        save_active_session(state, self.state_file, lock_timeout=self.lock_timeout)

        return state, ticket_text

    def get_hint(self) -> tuple[int, str, int, bool]:
        """Request the next mentor hint for the active session.

        Returns: (hint_level, hint_text, penalty, is_max)
        """
        state = self._require_active_state()
        fault = self._load_fault(state.fault_id)

        next_level = min(3, state.hint_level + 1)
        penalty = next_level * 5
        is_max = next_level >= 3

        if state.no_ai or self.settings.t2t_ai_provider == "none":
            hint_text = fault.hints.get(
                next_level,
                f"Review routing tables and redistribution for fault {fault.id}.",
            )
        else:
            provider = get_provider(self.settings, self.clock)
            hint_text = generate_hint(
                fault=fault,
                level=next_level,
                provider=provider,
                sink=self.store,
            )

        state.hint_level = next_level
        save_active_session(state, self.state_file, lock_timeout=self.lock_timeout)
        self.store.update_session(state.session_id, hints_used=next_level)

        return next_level, hint_text, penalty, is_max

    def submit_explanation(
        self,
        explanation: str,
    ) -> tuple[bool, list[CheckResult], DriftReport | None, ScoreBreakdown | None, str]:
        """Verify candidate fix, evaluate drift, grade explanation, and score session.

        Returns: (passed, check_results, drift_report, score_breakdown, feedback)
        """
        state = self._require_active_state()
        fault = self._load_fault(state.fault_id)
        self.store.set_active_session_id(state.session_id)

        # 1. Run fault verification checks
        with self._create_device_session() as session:
            results, passed = run_all(fault.checks, session, clock=self.clock)

        for r in results:
            self.store.record_check_result(
                session_id=state.session_id,
                attempt=state.failed_submits + 1,
                check_id=r.check_id,
                passed=r.passed,
                observed=r.observed,
            )

        # 2. If checks failed, stay ACTIVE and increment failed_submits
        if not passed:
            state.failed_submits += 1
            save_active_session(state, self.state_file, lock_timeout=self.lock_timeout)
            self.store.update_session(state.session_id, failed_submits=state.failed_submits)
            return (
                False,
                results,
                None,
                None,
                "Verification checks failed. Review the check results and router configurations.",
            )

        # 3. All checks passed: Evaluate configuration drift against baseline
        golden_configs: dict[str, str] = {}
        current_configs: dict[str, str] = {}
        with self._create_device_session() as session:
            for r_name in [r.name for r in self.inventory.routers]:
                cfg = session.show(r_name, "show running-config")
                current_configs[r_name] = cfg
                golden_configs[r_name] = cfg

        drift_report = check_drift(current_configs, golden_configs)

        # 4. Grade explanation
        now_ts = self.clock.now()
        start_ts = datetime.fromisoformat(state.started_at).timestamp()
        seconds = max(1, int(now_ts - start_ts))
        par_seconds = get_par_seconds(state.level)

        ai_score_10: int | None = None
        feedback = "Technical fix verified successfully."

        if not state.no_ai and self.settings.t2t_ai_provider != "none":
            provider = get_provider(self.settings, self.clock)
            grade = grade_explanation(
                explanation=explanation,
                fault=fault,
                provider=provider,
                sink=self.store,
            )
            if grade.available:
                ai_score_10 = grade.total
                feedback = grade.feedback

        # 5. Compute deterministic score
        score = compute_score(
            verified=True,
            clean_fix=drift_report.clean_fix,
            seconds=seconds,
            par_seconds=par_seconds,
            hints_used=state.hint_level,
            failed_submits=state.failed_submits,
            ai_score_10=ai_score_10,
            revealed=False,
        )

        # 6. Finalise session in database and clear state
        now_iso = datetime.fromtimestamp(now_ts, tz=UTC).isoformat()
        self.store.update_session(
            state.session_id,
            finished_at=now_iso,
            status="SOLVED",
            hints_used=state.hint_level,
            failed_submits=state.failed_submits,
            explanation=explanation,
            tech_score=score.technical_score,
            ai_score=score.explanation_score,
            final_score=score.total_score,
            seconds=seconds,
        )
        clear_active_session(self.state_file)

        return True, results, drift_report, score, feedback

    def reveal_fault(self) -> tuple[str, dict[str, list[str]], ScoreBreakdown]:
        """Reveal fault root cause and reference fix, forfeiting score.

        Transitions: ACTIVE -> REVEALED -> IDLE.
        """
        state = self._require_active_state()
        fault = self._load_fault(state.fault_id)

        now_ts = self.clock.now()
        start_ts = datetime.fromisoformat(state.started_at).timestamp()
        seconds = max(1, int(now_ts - start_ts))
        par_seconds = get_par_seconds(state.level)

        score = compute_score(
            verified=False,
            clean_fix=False,
            seconds=seconds,
            par_seconds=par_seconds,
            hints_used=state.hint_level,
            failed_submits=state.failed_submits,
            ai_score_10=None,
            revealed=True,
        )

        now_iso = datetime.fromtimestamp(now_ts, tz=UTC).isoformat()
        self.store.update_session(
            state.session_id,
            finished_at=now_iso,
            status="REVEALED",
            hints_used=state.hint_level,
            failed_submits=state.failed_submits,
            tech_score=0,
            ai_score=0,
            final_score=0,
            seconds=seconds,
        )

        # Apply revert on routers to restore healthy state
        with self._create_device_session() as session:
            engine = self._create_fault_engine(session)
            engine.revert(fault)
        clear_active_session(self.state_file)

        return fault.root_cause, fault.revert, score

    def abandon_session(self) -> None:
        """Abandon active session without scoring, restoring baseline.

        Transitions: ACTIVE -> ABANDONED -> IDLE.
        """
        state = self._require_active_state()
        fault = self._load_fault(state.fault_id)

        now_ts = self.clock.now()
        now_iso = datetime.fromtimestamp(now_ts, tz=UTC).isoformat()

        self.store.update_session(
            state.session_id,
            finished_at=now_iso,
            status="ABANDONED",
            tech_score=0,
            ai_score=0,
            final_score=0,
        )

        with self._create_device_session() as session:
            engine = self._create_fault_engine(session)
            engine.revert(fault)
        clear_active_session(self.state_file)
