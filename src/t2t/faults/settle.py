"""Settling and baseline convergence polling functions using injectable Clock.

NOTE: Per AGENTS.md Hard Rule 3, t2t.faults must never import t2t.ai.
"""

import logging
from typing import Any

from t2t.clock import Clock
from t2t.config import Inventory
from t2t.errors import T2TError
from t2t.models import Check, CheckResult
from t2t.verify.engine import run_all

logger = logging.getLogger(__name__)


def wait_for_baseline(
    session: Any,
    clock: Clock,
    baseline_checks: list[Check],
    timeout: float = 180.0,
    poll_interval: float = 5.0,
) -> list[CheckResult]:
    """Poll baseline checks until all pass or timeout is reached.

    Raises:
        T2TError: If timeout is reached while checks still fail.
    """
    start_time = clock.now()
    last_results: list[CheckResult] = []

    while True:
        results, passed = run_all(baseline_checks, session, clock)
        last_results = results
        if passed:
            logger.info("Baseline checks passed successfully.")
            return results

        elapsed = clock.now() - start_time
        if elapsed >= timeout:
            failing = [r.check_id for r in last_results if not r.passed]
            raise T2TError(
                f"Timed out waiting for baseline to pass ({elapsed:.1f}s >= {timeout:.1f}s). "
                f"Failing checks: {failing}"
            )

        clock.sleep(poll_interval)


def wait_for_settle(
    session: Any,
    clock: Clock,
    inventory: Inventory,
    stable_polls: int = 3,
    poll_interval: float = 5.0,
    timeout: float = 60.0,
) -> bool:
    """Wait for routing topology and neighbor tables to settle.

    Observation set: show commands across routers that capture routing & adjacencies.
    Done after stable_polls consecutive identical poll snapshots.
    On timeout, returns False with a warning.
    """
    start_time = clock.now()
    consecutive_matches = 0
    last_snapshot: list[str] = []

    # Routers to observe
    routers = [r.name for r in inventory.routers]

    while True:
        snapshot: list[str] = []
        for r_name in routers:
            try:
                # Capture neighbors and key route outputs
                out_eigrp = session.show(r_name, "show ip eigrp neighbors")
                out_ospf = session.show(r_name, "show ip ospf neighbor")
                snapshot.extend([out_eigrp, out_ospf])
            except Exception as err:
                snapshot.append(f"ERR: {err}")

        if last_snapshot and snapshot == last_snapshot:
            consecutive_matches += 1
            if consecutive_matches >= stable_polls - 1:
                logger.info(
                    "Network settled successfully across %d consecutive polls.",
                    stable_polls,
                )
                return True
        else:
            consecutive_matches = 0

        last_snapshot = snapshot
        elapsed = clock.now() - start_time
        if elapsed >= timeout:
            logger.warning(
                "Settling timeout reached (%0.1fs >= %0.1fs); network may not have converged.",
                elapsed,
                timeout,
            )
            return False

        clock.sleep(poll_interval)
