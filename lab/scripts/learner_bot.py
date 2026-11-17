"""Learner bot executing end-to-end qualification per fault (E6.1).

Validates autonomous learner workflow against catalog faults:
1. start_ticket (injects fault, initiates active session)
2. submit_explanation (must fail verification on faulted lab)
3. apply fault revert via DeviceSession.push_config
4. submit_explanation (must pass verification, compute score)
5. history verification
6. reset_lab to golden baseline before next fault

Usage:
    python lab/scripts/learner_bot.py --all
    python lab/scripts/learner_bot.py --fault T3
    python lab/scripts/learner_bot.py --all --replay
"""

import argparse
import sys
from pathlib import Path

from t2t.clock import Clock, FakeClock, SystemClock
from t2t.config import load_inventory, load_settings
from t2t.devices.session import DeviceSession
from t2t.faults.engine import FaultEngine
from t2t.faults.loader import FaultModel, load_baseline_checks, load_catalog
from t2t.session.models import SessionStatus
from t2t.session.service import SessionService
from t2t.session.store import SQLiteStore


def run_learner_bot(
    fault_ids: list[str] | None = None,
    replay: bool = False,
    no_ai: bool = True,
    clock: Clock | None = None,
) -> bool:
    """Execute automated learner bot run for specified or all catalog faults.

    Returns:
        True if all faults completed full pass/fail cycle successfully; False otherwise.
    """
    settings = load_settings()
    inventory = load_inventory(settings.t2t_inventory)
    baseline_path = Path("src/t2t/faults/baseline.yaml")
    baseline_checks = load_baseline_checks(baseline_path)
    catalog_path = Path("src/t2t/faults/catalog")
    catalog = load_catalog(catalog_path, inventory)

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

    # Filter catalog
    target_faults: list[FaultModel] = []
    if fault_ids:
        for fid in fault_ids:
            if fid not in catalog:
                print(f"Error: Fault {fid} not found in catalog {catalog_path}")
                return False
            target_faults.append(catalog[fid])
    else:
        target_faults = sorted(catalog.values(), key=lambda f: int(f.id.lstrip("T")))

    print(
        f"Learner Bot E6.1 starting for {len(target_faults)} fault(s) "
        f"(replay={replay}, no_ai={no_ai})..."
    )

    all_passed = True

    for fault in target_faults:
        print("\n==========================================")
        print(f"Executing Learner Bot cycle on: {fault.id} - {fault.title}")
        print("==========================================")

        # Ensure lab is reset to baseline first
        print("Ensuring clean baseline configuration...")
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
            engine.reset_lab(baseline_checks=baseline_checks)

        # Step 1: Start ticket (injects fault)
        print(f"[1/5] Starting ticket for fault {fault.id}...")
        try:
            state, ticket_text = service.start_ticket(fault_id=fault.id, no_ai=no_ai)
            print(f"      Session ID: {state.session_id}")
            print(f"      Active Fault: {state.fault_id}")
        except Exception as exc:
            print(f"      FAILED to start ticket: {exc}")
            all_passed = False
            continue

        # Step 2: Submit initial explanation without fix (MUST FAIL)
        print("[2/5] Submitting premature explanation (must fail)...")
        passed, checks, drift, breakdown, feedback = service.submit_explanation(
            explanation="Initial probe before identifying root cause."
        )
        if passed:
            print("      FAILED: Premature submission PASSED, but expected it to FAIL!")
            all_passed = False
            service.abandon_session()
            continue
        print("      PASS: Verification correctly failed as fault is active.")
        failed_checks = [c.check_id for c in checks if not c.passed]
        print(f"      Failing checks: {failed_checks}")

        # Step 3: Apply fix via DeviceSession.push_config (using fault revert definition)
        print("[3/5] Applying candidate fix using DeviceSession.push_config...")
        with DeviceSession(
            inventory=inventory,
            settings=settings,
            read_only=False,
            replay=replay,
            clock=clock,
        ) as session:
            for router, config_lines in fault.revert.items():
                print(f"      Pushing {len(config_lines)} lines to {router}...")
                session.push_config(router, config_lines)

            # Wait for protocol convergence
            engine = FaultEngine(session=session, clock=clock, inventory=inventory)
            print("      Waiting 5.0s for routing protocol settle...")
            engine.wait_for_settle(5.0)

        # Step 4: Submit explanation after fix (MUST PASS)
        print("[4/5] Submitting final explanation after fix (must pass)...")
        explanation_msg = (
            f"Identified and repaired route redistribution configuration for {fault.id}."
        )
        passed, checks, drift, breakdown, feedback = service.submit_explanation(
            explanation=explanation_msg
        )
        if not passed:
            print("      FAILED: Fix submission failed verification checks!")
            for c in checks:
                if not c.passed:
                    print(f"        - {c.check_id}: {c.observed}")
            all_passed = False
            service.abandon_session()
            continue

        print("      PASS: Verification checks passed!")
        if breakdown:
            print(
                f"      Score: {breakdown.final_score}/100 "
                f"(Base: {breakdown.base_score}, Hints: -{breakdown.hint_penalty}, "
                f"Time: -{breakdown.time_penalty}, Attempts: -{breakdown.attempt_penalty})"
            )

        # Step 5: Verify history and persistence
        print("[5/5] Verifying session status in SQLite store...")
        records = store.get_history(limit=5)
        latest = next((r for r in records if r.session_id == state.session_id), None)
        status_val = latest.status if latest else "None"
        if latest is None or latest.status != SessionStatus.SOLVED.value:
            print(f"      FAILED: History record status {status_val} != SOLVED")
            all_passed = False
        else:
            print(
                f"      PASS: Session recorded as {latest.status} with score {latest.final_score}."
            )

        # Clean reset for next iteration
        print("Restoring golden baseline...")
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
            engine.reset_lab(baseline_checks=baseline_checks)

    print("\n==========================================")
    if all_passed:
        print("Learner Bot E6.1 Run: ALL PASS")
    else:
        print("Learner Bot E6.1 Run: FAILURES DETECTED")
    print("==========================================")

    return all_passed


def main() -> None:
    """CLI entrypoint for learner bot."""
    parser = argparse.ArgumentParser(description="Autonomous learner bot for testing fault cycles.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run through all faults in catalog",
    )
    parser.add_argument(
        "--fault",
        type=str,
        default=None,
        help="Run specific fault ID (e.g. T3)",
    )
    parser.add_argument(
        "--replay",
        action="store_true",
        help="Run in offline replay mode against mock fixtures",
    )
    parser.add_argument(
        "--with-ai",
        action="store_true",
        help="Enable AI generation/grading (defaults to no-ai deterministic)",
    )

    args = parser.parse_args()

    fault_ids = None
    if args.fault:
        fault_ids = [args.fault.upper()]
    elif not args.all:
        print("Error: Specify either --all or --fault <ID>")
        sys.exit(2)

    success = run_learner_bot(
        fault_ids=fault_ids,
        replay=args.replay,
        no_ai=not args.with_ai,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
