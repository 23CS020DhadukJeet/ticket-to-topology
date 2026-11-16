"""Fault qualification harness proving fault behavior and generating evidence reports.

NOTE: Per AGENTS.md Hard Rule 3, t2t.faults must never import t2t.ai.
"""

import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from t2t.devices.slug import slug
from t2t.faults.engine import FaultEngine
from t2t.faults.loader import FaultModel
from t2t.models import Check
from t2t.verify.engine import run_all

logger = logging.getLogger(__name__)

# Standard capture command list from BUILD_GUIDE Phase 1 & 4
CAPTURE_COMMANDS = [
    "show version",
    "show ip route",
    "show ip protocols",
    "show ip eigrp neighbors",
    "show ip ospf neighbor",
    "show route-map",
    "show running-config | section router|route-map|prefix-list",
    "show ip route 10.10.1.0 255.255.255.0",
    "show ip route 10.10.2.0 255.255.255.0",
    "show ip route 10.10.99.0 255.255.255.0",
    "show ip route 172.16.10.0 255.255.255.0",
    "show ip route 172.16.20.16 255.255.255.240",
]


class QualificationRun(BaseModel):
    """Result of a single qualification run for a fault."""

    run_number: int
    baseline_pre_passed: bool
    fault_checks_pre_passed: bool
    inject_failed_checks: list[str]
    revert_passed: bool
    baseline_post_passed: bool
    duration_s: float
    success: bool


class QualificationReport(BaseModel):
    """Full qualification report for a fault."""

    fault_id: str
    title: str
    qualified: bool
    runs: list[QualificationRun]
    observed_symptom: str
    total_duration_s: float
    generated_at: str


def _capture_router_fixtures(
    session: Any, fault_id: str, fixtures_root: Path, inventory_routers: list[str]
) -> None:
    """Capture raw router outputs into tests/fixtures/faulted/<ID>/<ROUTER>/."""
    for r_name in inventory_routers:
        r_dir = fixtures_root / "faulted" / fault_id / r_name
        r_dir.mkdir(parents=True, exist_ok=True)
        for cmd in CAPTURE_COMMANDS:
            try:
                out = session.show(r_name, cmd)
                f_name = f"{slug(cmd)}.txt"
                (r_dir / f_name).write_text(out, encoding="utf-8")
            except Exception as err:
                logger.warning("Failed to capture '%s' on %s: %s", cmd, r_name, err)


def qualify_fault(
    fault: FaultModel,
    engine: FaultEngine,
    baseline_checks: list[Check],
    runs: int = 3,
    capture: bool = False,
    report_dir: Path = Path("docs/evidence/phase4"),
    fixtures_root: Path = Path("tests/fixtures"),
) -> QualificationReport:
    """Run N qualification cycles on a fault and write evidence reports."""
    t_start = time.perf_counter()
    report_dir.mkdir(parents=True, exist_ok=True)
    qualification_runs: list[QualificationRun] = []
    observed_symptoms_list: list[str] = []

    for run_idx in range(1, runs + 1):
        r_start = time.perf_counter()
        logger.info("Starting qualification run %d/%d for fault %s", run_idx, runs, fault.id)

        # 1. Reset lab & verify baseline
        pre_reset = engine.reset_lab(baseline_checks)
        resets_ok = all(s.success for s in pre_reset.values())
        if not resets_ok:
            logger.warning(
                "Qualification run %d: Reset failed on routers: %s",
                run_idx,
                [r for r, s in pre_reset.items() if not s.success],
            )
            pre_base_passed = False
        else:
            results_pre_base, pre_base_passed = run_all(
                baseline_checks, engine.session, engine.clock
            )

        # 2. Assert all fault checks pass on baseline (precondition)
        results_pre_fault, pre_fault_passed = run_all(fault.checks, engine.session, engine.clock)

        # 3. Inject fault & settle
        engine.inject(fault, skip_baseline_check=True)

        # 4. Run checks, require >= 1 failure
        results_inject, inject_verdict = run_all(fault.checks, engine.session, engine.clock)
        failed_checks = [r.check_id for r in results_inject if not r.passed]

        # 5. Capture if requested
        if capture and run_idx == 1:
            router_names = [r.name for r in engine.inventory.routers]
            _capture_router_fixtures(engine.session, fault.id, fixtures_root, router_names)

            # Build observed symptom summary
            symptom_parts = []
            for r in results_inject:
                if not r.passed:
                    symptom_parts.append(f"Check {r.check_id} failed: {r.message}")
            if symptom_parts:
                observed_symptoms_list.append("; ".join(symptom_parts))

        # 6. Revert fault & settle
        engine.revert(fault)

        # 7. Require all fault checks pass after revert
        results_post_revert, post_revert_passed = run_all(
            fault.checks, engine.session, engine.clock
        )

        # 8. Reset lab & verify baseline
        post_reset = engine.reset_lab(baseline_checks)
        post_resets_ok = all(s.success for s in post_reset.values())
        if not post_resets_ok:
            post_base_passed = False
        else:
            results_post_base, post_base_passed = run_all(
                baseline_checks, engine.session, engine.clock
            )

        run_duration = round(time.perf_counter() - r_start, 2)
        run_success = (
            pre_base_passed
            and pre_fault_passed
            and (len(failed_checks) > 0)
            and post_revert_passed
            and post_base_passed
        )

        qualification_runs.append(
            QualificationRun(
                run_number=run_idx,
                baseline_pre_passed=pre_base_passed,
                fault_checks_pre_passed=pre_fault_passed,
                inject_failed_checks=failed_checks,
                revert_passed=post_revert_passed,
                baseline_post_passed=post_base_passed,
                duration_s=run_duration,
                success=run_success,
            )
        )

    total_duration = round(time.perf_counter() - t_start, 2)
    all_runs_passed = all(qr.success for qr in qualification_runs)
    final_symptom = (
        observed_symptoms_list[0]
        if observed_symptoms_list
        else (fault.observed_symptom or "Qualified symptom observed")
    )

    report = QualificationReport(
        fault_id=fault.id,
        title=fault.title,
        qualified=all_runs_passed,
        runs=qualification_runs,
        observed_symptom=final_symptom,
        total_duration_s=total_duration,
        generated_at=datetime.now(UTC).isoformat(),
    )

    # Write JSON report
    json_path = report_dir / f"qualification-{fault.id}.json"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    # Write Markdown report
    md_path = report_dir / f"qualification-{fault.id}.md"
    md_content = _render_markdown_report(report)
    md_path.write_text(md_content, encoding="utf-8")

    return report


def _render_markdown_report(report: QualificationReport) -> str:
    """Render qualification report as GitHub-flavored Markdown."""
    status_str = "**QUALIFIED (PASS)**" if report.qualified else "**DISQUALIFIED (FAIL)**"
    lines = [
        f"# Qualification Report: {report.fault_id} — {report.title}",
        "",
        f"- **Status:** {status_str}",
        f"- **Total Duration:** {report.total_duration_s}s",
        f"- **Generated At:** `{report.generated_at}`",
        f"- **Observed Symptom:** {report.observed_symptom}",
        "",
        "## Qualification Runs",
        "",
        (
            "| Run | Baseline Pre | Fault Checks Pre | Injected Failing Checks | "
            "Revert Pass | Baseline Post | Duration | Verdict |"
        ),
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in report.runs:
        verdict = "PASS" if r.success else "FAIL"
        failing_str = ", ".join(r.inject_failed_checks) if r.inject_failed_checks else "None"
        lines.append(
            f"| {r.run_number} | {r.baseline_pre_passed} | {r.fault_checks_pre_passed} | "
            f"`{failing_str}` | {r.revert_passed} | {r.baseline_post_passed} | "
            f"{r.duration_s}s | **{verdict}** |"
        )
    lines.append("")
    return "\n".join(lines)


def qualify_all(
    catalog: dict[str, FaultModel],
    engine: FaultEngine,
    baseline_checks: list[Check],
    runs: int = 3,
    capture: bool = False,
    report_dir: Path = Path("docs/evidence/phase4"),
) -> list[QualificationReport]:
    """Qualify all faults in catalog consecutively."""
    reports: list[QualificationReport] = []
    for fault_id, fault in sorted(catalog.items()):
        logger.info("Qualifying fault %s (%s)...", fault_id, fault.title)
        rep = qualify_fault(
            fault=fault,
            engine=engine,
            baseline_checks=baseline_checks,
            runs=runs,
            capture=capture,
            report_dir=report_dir,
        )
        reports.append(rep)
    return reports
