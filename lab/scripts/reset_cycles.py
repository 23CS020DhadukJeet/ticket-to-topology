"""Measure consecutive reset and baseline cycles on the lab (Objective O2).

Usage:
    python lab/scripts/reset_cycles.py [CYCLES]
"""

import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from t2t.config import load_inventory, load_settings
from t2t.devices.session import DeviceSession
from t2t.faults.engine import FaultEngine
from t2t.faults.loader import load_baseline_checks


def run_reset_cycles(cycles: int = 20, replay: bool = False) -> None:
    """Run consecutive reset+baseline cycles and report timings."""
    settings = load_settings()
    inventory = load_inventory(settings.t2t_inventory)
    baseline_path = Path("src/t2t/faults/baseline.yaml")
    baseline_checks = load_baseline_checks(baseline_path)

    durations: list[float] = []
    failures = 0

    print(f"Starting {cycles} consecutive reset+baseline cycles...")

    with DeviceSession(
        inventory=inventory, settings=settings, read_only=False, replay=replay
    ) as session:
        engine = FaultEngine(
            session=session,
            inventory=inventory,
            baseline_checks=baseline_checks,
        )

        for i in range(1, cycles + 1):
            t_start = time.perf_counter()
            try:
                statuses = engine.reset_lab(baseline_checks=baseline_checks)
                failed_routers = [r for r, s in statuses.items() if not s.success]
                if failed_routers:
                    print(f"Cycle {i}/{cycles}: FAILED on {failed_routers}")
                    failures += 1
                else:
                    duration = round(time.perf_counter() - t_start, 2)
                    durations.append(duration)
                    print(f"Cycle {i}/{cycles}: OK in {duration}s")
            except Exception as err:
                print(f"Cycle {i}/{cycles}: EXCEPTION - {err}")
                failures += 1

    median_duration = statistics.median(durations) if durations else 0.0
    mean_duration = statistics.mean(durations) if durations else 0.0

    print("\n--- Summary ---")
    print(f"Total Cycles: {cycles}")
    print(f"Passed: {len(durations)}/{cycles}")
    print(f"Failures: {failures}")
    print(f"Median Time: {median_duration:.2f}s")
    print(f"Mean Time: {mean_duration:.2f}s")

    # Write evidence report
    evidence_dir = Path("docs/evidence/phase4")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    report_file = evidence_dir / "reset-cycles.md"

    md_lines = [
        "# Reset Cycles Benchmark (Objective O2)",
        "",
        f"- **Date:** `{datetime.now(UTC).isoformat()}`",
        f"- **Cycles Attempted:** {cycles}",
        f"- **Successful Cycles:** {len(durations)}",
        f"- **Failed Cycles:** {failures}",
        f"- **Median Duration:** {median_duration:.2f}s",
        f"- **Mean Duration:** {mean_duration:.2f}s",
        "",
        "## Cycle Durations",
        "",
        "| Cycle | Duration (s) | Status |",
        "|---|---|---|",
    ]
    for idx, d in enumerate(durations, 1):
        md_lines.append(f"| {idx} | {d:.2f} | PASS |")
    md_lines.append("")

    report_file.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Saved benchmark report to {report_file}")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    run_reset_cycles(cycles=count)
