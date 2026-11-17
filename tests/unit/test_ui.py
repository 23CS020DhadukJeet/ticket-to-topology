"""Unit tests for Phase 6 Rich UI components and NO_COLOR support (U6.5)."""

import os
import re
from unittest import mock

from t2t.cli.ui import (
    get_console,
    render_check_results,
    render_closing_card,
    render_hint_card,
    render_ticket_card,
)
from t2t.models import CheckResult
from t2t.session.drift import DriftReport
from t2t.session.scoring import compute_score


def test_u6_5_ticket_card_rendering() -> None:
    """Verify red ticket card includes all required incident fields."""
    panel = render_ticket_card(
        ticket_text="Users report high latency to vendor services.",
        fault_id="T3",
        level=2,
        symptom_class="suboptimal",
        flows=[{"src": "172.16.10.10", "dst": "10.10.99.1", "note": "HQ to vendor"}],
    )
    console = get_console()
    with console.capture() as capture:
        console.print(panel)
    output = capture.get()

    assert "T3" in output
    assert "Level 2" in output
    assert "suboptimal" in output.lower()
    assert "Users report high latency" in output
    assert "172.16.10.10" in output


def test_u6_5_hint_card_rendering() -> None:
    """Verify yellow hint card displays level, penalty, and maximum level notice."""
    panel_l1 = render_hint_card(
        hint_text="Inspect routing on R3.",
        level=1,
        penalty=5,
        is_max=False,
    )
    console = get_console()
    with console.capture() as capture:
        console.print(panel_l1)
    output_l1 = capture.get()
    assert "Hint 1/3" in output_l1
    assert "Cost: -5 pts" in output_l1
    assert "Inspect routing on R3." in output_l1

    panel_max = render_hint_card(
        hint_text="Show ip route 10.10.99.0.",
        level=3,
        penalty=15,
        is_max=True,
    )
    with console.capture() as capture:
        console.print(panel_max)
    output_max = capture.get()
    assert "Maximum hint level reached" in output_max


def test_u6_5_closing_card_rendering() -> None:
    """Verify green closing card presents full score breakdown and drift summary."""
    score = compute_score(
        verified=True,
        clean_fix=True,
        seconds=450,
        par_seconds=900,
        hints_used=1,
        failed_submits=0,
        ai_score_10=9,
    )
    drift = DriftReport(clean_fix=True, diffs={}, summary="No configuration drift detected.")
    panel = render_closing_card(
        score=score,
        drift=drift,
        feedback="Excellent root-cause explanation.",
    )
    console = get_console()
    with console.capture() as capture:
        console.print(panel)
    output = capture.get()

    assert "Session Completed" in output
    assert "Final Score" in output
    assert "Verification: 40/40" in output
    assert "Clean Fix: 10/10" in output
    assert "Excellent root-cause explanation" in output


def test_u6_5_check_results_table() -> None:
    """Verify check results table formats PASS and FAIL badges."""
    results = [
        CheckResult(
            check_id="c1",
            passed=True,
            expected="10.10.99.0/24 in RIB",
            observed="10.10.99.0/24 via 10.1.13.1",
            message="Check passed",
        ),
        CheckResult(
            check_id="c2",
            passed=False,
            expected="distance 170",
            observed="distance 110",
            message="Distance mismatch",
        ),
    ]
    table = render_check_results(results)
    console = get_console()
    with console.capture() as capture:
        console.print(table)
    output = capture.get()

    assert "c1" in output
    assert "PASS" in output
    assert "c2" in output
    assert "FAIL" in output


def test_u6_5_no_color_plain_mode() -> None:
    """When NO_COLOR is set, get_console must produce plain text without ANSI escape sequences."""
    with mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
        console = get_console()
        assert console.no_color is True
        assert console.color_system is None

        panel = render_ticket_card(
            ticket_text="Plain ticket",
            fault_id="T1",
            level=1,
            symptom_class="latent",
            flows=[],
        )
        with console.capture() as capture:
            console.print(panel)
        output = capture.get()

        # Check there are no ANSI escape sequences
        ansi_regex = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
        assert not ansi_regex.search(output)
