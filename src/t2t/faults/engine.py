"""Fault injection, revert, and lab reset orchestration engine.

NOTE: Per AGENTS.md Hard Rule 3, t2t.faults must never import t2t.ai.
NOTE: Per AGENTS.md Hard Rule 4, all configuration changes go through DeviceSession.push_config.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from pydantic import BaseModel

from t2t.clock import Clock, SystemClock
from t2t.config import Inventory
from t2t.devices.session import DeviceSession
from t2t.errors import T2TError
from t2t.faults.loader import FaultModel
from t2t.faults.settle import wait_for_baseline, wait_for_settle
from t2t.faults.state import clear_active_fault, get_state, set_active_fault
from t2t.models import Check

logger = logging.getLogger(__name__)


class RouterResetStatus(BaseModel):
    """Result of running configure replace on a router."""

    router: str
    success: bool
    duration_s: float
    output: str


class FaultEngine:
    """Manages injecting faults, reverting changes, and resetting routers to baseline."""

    def __init__(
        self,
        session: DeviceSession,
        clock: Clock | None = None,
        inventory: Inventory | None = None,
        state_file: Path = Path(".t2t/state.json"),
        baseline_checks: list[Check] | None = None,
    ) -> None:
        self.session = session
        self.clock: Clock = clock if clock is not None else SystemClock()
        self.inventory: Inventory = inventory or session.inventory
        self.state_file = state_file
        self.baseline_checks = baseline_checks or []

    def inject(self, fault: FaultModel, skip_baseline_check: bool = False) -> None:
        """Inject a fault across configured routers.

        1. Verify no existing fault is active.
        2. Optionally verify baseline is currently healthy.
        3. Push inject configuration per router via session.push_config.
        4. Update MockDevice scenarios if in replay/mock mode.
        5. Record active fault in state file.
        6. Wait for network to settle.
        """
        current_state = get_state(self.state_file)
        if current_state.active_fault is not None:
            raise T2TError(
                f"Cannot inject '{fault.id}': another fault '{current_state.active_fault}' "
                "is already active. Run 't2t reset' first."
            )

        if not skip_baseline_check and self.baseline_checks:
            logger.info("Verifying baseline before fault injection...")
            wait_for_baseline(self.session, self.clock, self.baseline_checks, timeout=60.0)

        # Push configuration per router
        for r_name, commands in fault.inject.items():
            logger.info("Injecting %s config on %s: %s", fault.id, r_name, commands)
            self.session.push_config(r_name, commands, reason=f"inject {fault.id}")

        # Update mock devices scenario if applicable
        for r_name in fault.inject:
            dev = self.session.devices.get(r_name)
            if dev is not None and hasattr(dev, "set_scenario"):
                dev.set_scenario(f"faulted/{fault.id}")
            elif dev is not None and hasattr(dev, "scenario"):
                dev.scenario = f"faulted/{fault.id}"

        # Record in state file
        set_active_fault(fault.id, self.state_file)

        # Settle network
        wait_for_settle(self.session, self.clock, self.inventory)
        logger.info("Fault %s injected and settled successfully.", fault.id)

    def revert(self, fault: FaultModel) -> None:
        """Revert a fault using its reference fix configuration.

        1. Push revert configuration per router via session.push_config.
        2. Reset MockDevice scenarios back to baseline.
        3. Settle network.
        4. Clear active fault from state file.
        """
        logger.info("Reverting fault %s...", fault.id)
        for r_name, commands in fault.revert.items():
            logger.info("Reverting %s on %s: %s", fault.id, r_name, commands)
            self.session.push_config(r_name, commands, reason=f"revert {fault.id}")

        # Update mock devices scenario back to baseline
        for r_name in fault.revert:
            dev = self.session.devices.get(r_name)
            if dev is not None and hasattr(dev, "set_scenario"):
                dev.set_scenario("baseline")
            elif dev is not None and hasattr(dev, "scenario"):
                dev.scenario = "baseline"

        # Settle network
        wait_for_settle(self.session, self.clock, self.inventory)

        # Clear state
        clear_active_fault(self.state_file)
        logger.info("Fault %s reverted and state cleared.", fault.id)

    def reset_lab(
        self,
        baseline_checks: list[Check] | None = None,
        golden_path: str | None = None,
        timeout_per_router: float = 120.0,
    ) -> dict[str, RouterResetStatus]:
        """Restore all routers to baseline in parallel via configure replace.

        Per BUILD_GUIDE Phase 4:
        Runs 'configure replace <golden_path> force' in parallel threads,
        clears active fault, then waits for baseline.
        """
        target_checks = baseline_checks or self.baseline_checks
        default_golden = self.inventory.defaults.get("golden_path", "flash:golden.cfg")
        replace_path = golden_path or default_golden

        results: dict[str, RouterResetStatus] = {}

        def _reset_single(r_name: str) -> RouterResetStatus:
            t_start = time.perf_counter()
            cmd = f"configure replace {replace_path} force"
            try:
                # Mock scenario update
                dev = self.session.devices.get(r_name)
                if dev is not None and hasattr(dev, "set_scenario"):
                    dev.set_scenario("baseline")
                elif dev is not None and hasattr(dev, "scenario"):
                    dev.scenario = "baseline"

                out = self.session.push_config(r_name, [cmd], reason="reset_lab")
                duration = time.perf_counter() - t_start
                # Check for errors in output
                failed = (
                    "failed" in out.lower()
                    or "error" in out.lower()
                    or "% " in out
                    or "abort" in out.lower()
                )
                return RouterResetStatus(
                    router=r_name,
                    success=not failed,
                    duration_s=round(duration, 2),
                    output=out,
                )
            except Exception as err:
                duration = time.perf_counter() - t_start
                return RouterResetStatus(
                    router=r_name,
                    success=False,
                    duration_s=round(duration, 2),
                    output=f"Reset exception: {err}",
                )

        # Run configure replace in parallel across all inventory routers
        router_names = [r.name for r in self.inventory.routers]
        with ThreadPoolExecutor(max_workers=len(router_names) or 1) as executor:
            future_to_router = {
                executor.submit(_reset_single, r_name): r_name for r_name in router_names
            }
            for future in as_completed(future_to_router):
                status = future.result()
                results[status.router] = status

        # Clear state file
        clear_active_fault(self.state_file, force=True)

        # Check for any failures
        failed_routers = [r for r, s in results.items() if not s.success]
        if failed_routers:
            logger.error(
                "Router reset failed on %s. Runbook: Verify golden_path (%s) and archive config; "
                "or reload routers.",
                failed_routers,
                replace_path,
            )

        # Wait for baseline if checks available and reset succeeded on all routers
        if target_checks and not failed_routers:
            try:
                wait_for_baseline(self.session, self.clock, target_checks, timeout=180.0)
            except Exception as err:
                logger.error(
                    "Baseline convergence failed after lab reset: %s. "
                    "Runbook: Check show ip eigrp/ospf neighbors and restore snapshot.",
                    err,
                )
                raise

        return results
