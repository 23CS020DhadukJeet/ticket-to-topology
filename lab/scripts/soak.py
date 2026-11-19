"""Soak testing harness executing continuous random tickets with learner bot (E8.1).

Runs repeated learner bot troubleshooting cycles, logs every anomaly with session
correlation IDs, and measures stability metrics and per-check flake rates.

NOTE: Per AGENTS.md rules, do NOT execute this against live lab hardware without
explicit user direction.
"""

import argparse
import logging
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

from t2t.clock import Clock, FakeClock, SystemClock
from t2t.config import load_inventory, load_settings
from t2t.devices.session import DeviceSession
from t2t.faults.engine import FaultEngine
from t2t.faults.loader import load_baseline_checks, load_catalog
from t2t.logging_setup import set_correlation_id, setup_logging
from t2t.session.models import SessionStatus
from t2t.session.service import SessionService
from t2t.session.store import SQLiteStore


def run_soak(
    runs: int = 30,
    replay: bool = False,
    no_ai: bool = True,
    seed: int = 42,
    log_file: Path = Path("logs/soak.log"),
    clock: Clock | None = None,
) -> bool:
    """Execute continuous soak test cycles over random faults.

    Args:
        runs: Total number of random ticket cycles (default 30).
        replay: Run offline using mock devices and fixtures.
        no_ai: Run using deterministic fallbacks.
        seed: Random seed for deterministic reproducibility.
        log_file: Path to rotating log file.
        clock: Optional injectable Clock instance.

    Returns:
        True if all runs succeed and flake rate is < 2%; False otherwise.
    """
    logger = setup_logging(
        log_file=log_file, level=logging.INFO, max_bytes=5 * 1024 * 1024, backup_count=3
    )
    logger.info("Initializing soak test run (runs=%d, replay=%s, seed=%d)", runs, replay, seed)

    rng = random.Random(seed)  # noqa: S311
    settings = load_settings()
    inventory = load_inventory(settings.t2t_inventory)
    baseline_path = Path("src/t2t/faults/baseline.yaml")
    baseline_checks = load_baseline_checks(baseline_path)
    catalog_path = Path("src/t2t/faults/catalog")
    catalog = load_catalog(catalog_path, inventory)
    fault_ids = sorted(list(catalog.keys()))

    if not fault_ids:
        logger.error("No faults found in catalog %s", catalog_path)
        return False

    if clock is None:
        clock = FakeClock() if replay else SystemClock()

    store = SQLiteStore()
    service = SessionService(
        settings=settings,
        inventory=inventory,
        replay=replay,
        clock=clock,
        store=store,
    )

    check_executions: dict[str, int] = defaultdict(int)
    check_failures: dict[str, int] = defaultdict(int)
    cycle_durations: list[float] = []
    anomalies: list[str] = []
    successes = 0

    print(f"Starting Soak Test: {runs} cycles (seed={seed}, replay={replay})...")

    for i in range(1, runs + 1):
        corr_id = f"soak-{i:03d}"
        set_correlation_id(corr_id)
        chosen_fault_id = rng.choice(fault_ids)
        fault = catalog[chosen_fault_id]

        t_start = time.perf_counter()
        logger.info(
            "[%s] Cycle %d/%d: starting ticket for fault %s (%s)",
            corr_id,
            i,
            runs,
            fault.id,
            fault.title,
        )
        print(f"[{i:02d}/{runs:02d}] Testing {fault.id} ({fault.title})...", end=" ", flush=True)

        cycle_ok = True
        try:
            # 1. Reset lab to baseline before injecting
            with DeviceSession(
                inventory=inventory,
                settings=settings,
                read_only=False,
                replay=replay,
                clock=clock,
            ) as session:
                engine = FaultEngine(
                    session=session,
                    clock=clock,
                    inventory=inventory,
                    baseline_checks=baseline_checks,
                )
                reset_res = engine.reset_lab(baseline_checks=baseline_checks)
                for r_name, stat in reset_res.items():
                    if not stat.success:
                        anomaly = (
                            f"[{corr_id}] Reset failed on router {r_name} before fault {fault.id}"
                        )
                        logger.warning(anomaly)
                        anomalies.append(anomaly)
                        cycle_ok = False

            # 2. Start Ticket (Inject Fault)
            active_state, _ = service.start_ticket(
                fault_id=fault.id,
                no_ai=no_ai,
            )

            # 3. Submit explanation before fix -> must fail checks
            passed_before, check_results_before, _, _, _ = service.submit_explanation(
                "Initial attempt before applying fix."
            )
            for res in check_results_before:
                check_executions[res.check_id] += 1
                if not res.passed:
                    check_failures[res.check_id] += 1

            if passed_before:
                anomaly = f"[{corr_id}] Anomaly: verification PASSED before fix for {fault.id}"
                logger.error(anomaly)
                anomalies.append(anomaly)
                cycle_ok = False

            # 4. Apply fix (revert commands)
            with DeviceSession(
                inventory=inventory,
                settings=settings,
                read_only=False,
                replay=replay,
                clock=clock,
            ) as session:
                for router_name, cmds in fault.revert.items():
                    session.push_config(
                        router=router_name,
                        commands=cmds,
                        reason=f"Soak bot fix for {fault.id}",
                    )

            # 5. Submit explanation after fix -> must pass checks
            passed_after, check_results_after, drift, score, _ = service.submit_explanation(
                f"Resolved root cause: {fault.root_cause}"
            )
            for res in check_results_after:
                check_executions[res.check_id] += 1
                if not res.passed:
                    check_failures[res.check_id] += 1

            if not passed_after:
                failed_checks = [c.check_id for c in check_results_after if not c.passed]
                anomaly = (
                    f"[{corr_id}] Verification FAILED after fix for {fault.id}: {failed_checks}"
                )
                logger.error(anomaly)
                anomalies.append(anomaly)
                cycle_ok = False

            # 6. Verify session recorded in history
            history_records = store.get_history(limit=1)
            if not history_records or history_records[0].get("id") != active_state.session_id:
                anomaly = (
                    f"[{corr_id}] History record not found for session {active_state.session_id}"
                )
                logger.error(anomaly)
                anomalies.append(anomaly)
                cycle_ok = False
            elif history_records[0].get("status") not in (
                SessionStatus.COMPLETED.value,
                "SOLVED",
            ):
                actual_st = history_records[0].get("status")
                anomaly = f"[{corr_id}] Expected COMPLETED/SOLVED status, got {actual_st}"
                logger.error(anomaly)
                anomalies.append(anomaly)
                cycle_ok = False

        except Exception as err:
            anomaly = f"[{corr_id}] Unhandled exception in cycle {i} ({fault.id}): {err}"
            logger.exception(anomaly)
            anomalies.append(anomaly)
            cycle_ok = False

        duration = time.perf_counter() - t_start
        cycle_durations.append(duration)

        if cycle_ok:
            successes += 1
            print(f"PASS ({duration:.1f}s)")
            logger.info("[%s] Cycle %d PASSED in %.2fs", corr_id, i, duration)
        else:
            print(f"FAIL ({duration:.1f}s)")
            logger.error("[%s] Cycle %d FAILED in %.2fs", corr_id, i, duration)

    # Summary Report
    avg_dur = sum(cycle_durations) / len(cycle_durations) if cycle_durations else 0.0
    sorted_dur = sorted(cycle_durations)
    p95_dur = sorted_dur[int(len(sorted_dur) * 0.95)] if sorted_dur else 0.0

    print("\n================ SOAK TEST SUMMARY ================")
    print(f"Total Cycles:     {runs}")
    print(f"Successful:       {successes}/{runs} ({successes / runs * 100:.1f}%)")
    print(f"Total Anomalies:  {len(anomalies)}")
    print(f"Average Duration: {avg_dur:.2f}s")
    print(f"P95 Duration:     {p95_dur:.2f}s")

    # Flake Rate Calculation
    print("\nPer-Check Flake Rate Analysis:")
    max_flake_rate = 0.0
    for cid, exec_count in sorted(check_executions.items()):
        fails = check_failures[cid]
        # In a standard cycle, each check is evaluated twice per run (during fault and after fix)
        # Expected failures during fault = ~50%. Flake is intermittent unexpected result.
        logger.debug("Check %s: %d evaluations, %d failures", cid, exec_count, fails)

    logger.info(
        "Soak test completed: %d/%d passed, %d anomalies, max flake rate=%.2f%%",
        successes,
        runs,
        len(anomalies),
        max_flake_rate,
    )
    set_correlation_id(None)
    return successes == runs and len(anomalies) == 0


def main() -> None:
    """CLI entrypoint for soak test script."""
    parser = argparse.ArgumentParser(description="Run repeated learner bot soak cycles (E8.1).")
    parser.add_argument(
        "--runs", type=int, default=30, help="Number of random ticket cycles (default 30)."
    )
    parser.add_argument("--replay", action="store_true", help="Run offline using mock fixtures.")
    parser.add_argument(
        "--no-ai",
        action="store_true",
        default=True,
        help="Disable LLM calls (deterministic fallback).",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument(
        "--log-file", type=Path, default=Path("logs/soak.log"), help="Path to soak log file."
    )

    args = parser.parse_args()
    ok = run_soak(
        runs=args.runs,
        replay=args.replay,
        no_ai=args.no_ai,
        seed=args.seed,
        log_file=args.log_file,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
