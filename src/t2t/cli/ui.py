"""Rich UI components, incident panels, badges, and NO_COLOR support.

Per BUILD_GUIDE Phase 6:
Rich panels: red ticket card, yellow hint card, green closing card;
PASS/FAIL badges; spinners during polling;
Plain mode honouring NO_COLOR for logs/CI.
"""

import os
from typing import Any

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from t2t.models import CheckResult
from t2t.session.drift import DriftReport
from t2t.session.scoring import ScoreBreakdown


def get_console() -> Console:
    """Return a Rich Console instance, respecting the NO_COLOR standard."""
    no_color_env = os.environ.get("NO_COLOR", "").strip()
    if no_color_env:
        return Console(no_color=True, color_system=None)
    return Console()


def render_ticket_card(
    ticket_text: str,
    fault_id: str,
    level: int,
    symptom_class: str,
    flows: list[Any],
) -> Panel:
    """Render the initial red incident ticket card."""
    lines: list[str] = [
        f"[bold]Fault ID:[/bold] {fault_id}  |  "
        f"[bold]Level:[/bold] Level {level}  |  "
        f"[bold]Symptom Class:[/bold] {symptom_class.upper()}",
        "",
    ]

    if flows:
        lines.append("[bold]Reported Business Flows:[/bold]")
        for flow in flows:
            if isinstance(flow, dict):
                src = flow.get("src", "")
                dst = flow.get("dst", "")
                note = flow.get("note", "")
            else:
                src = getattr(flow, "src", "")
                dst = getattr(flow, "dst", "")
                note = getattr(flow, "note", "")
            lines.append(f"  • {src} -> {dst} ({note})")
        lines.append("")

    lines.append("[bold]Incident Report:[/bold]")
    lines.append(f"  {ticket_text}")

    content = "\n".join(lines)
    return Panel(
        content,
        title=f"[bold red]INCIDENT TICKET: {fault_id}[/bold red]",
        border_style="red",
        padding=(1, 2),
    )


def render_hint_card(
    hint_text: str,
    level: int,
    penalty: int,
    is_max: bool = False,
) -> Panel:
    """Render a yellow mentor hint card."""
    lines: list[str] = [
        f"[bold]Hint {level}/3[/bold]  |  [bold yellow]Cost: -{penalty} pts[/bold yellow]",
        "",
        f"[italic]{hint_text}[/italic]",
    ]

    if is_max:
        lines.append("")
        lines.append(
            "[bold yellow]Notice:[/bold yellow] Maximum hint level reached (Level 3). "
            "No further hints available."
        )

    content = "\n".join(lines)
    return Panel(
        content,
        title=f"[bold yellow]MENTOR GUIDANCE (Level {level})[/bold yellow]",
        border_style="yellow",
        padding=(1, 2),
    )


def render_closing_card(
    score: ScoreBreakdown,
    drift: DriftReport,
    feedback: str = "",
    root_cause: str | None = None,
) -> Panel:
    """Render the green final score and debriefing card."""
    breakdown_table = Table.grid(padding=(0, 2))
    breakdown_table.add_column(style="bold")
    breakdown_table.add_column()

    breakdown_table.add_row("Verification: 40/40", f"{score.verification_score} / 40 pts")
    clean_str = "Clean (0 drift)" if score.clean_fix else "Drift detected"
    breakdown_table.add_row("Clean Fix: 10/10", f"{score.clean_fix_score} / 10 pts ({clean_str})")
    breakdown_table.add_row(
        f"Time Bonus (Par: {score.par_seconds}s, Took: {score.seconds}s):",
        f"{score.time_bonus} / 10 pts",
    )

    if score.explanation_score is not None:
        breakdown_table.add_row("Explanation Quality:", f"{score.explanation_score} / 40 pts")
    else:
        breakdown_table.add_row("Explanation Quality:", "N/A (--no-ai mode)")

    if score.hints_penalty > 0:
        breakdown_table.add_row(
            "Hints Penalty:", f"-{score.hints_penalty} pts ({score.hints_used} hints)"
        )
    if score.submits_penalty > 0:
        breakdown_table.add_row(
            "Failed Submits Penalty:",
            f"-{score.submits_penalty} pts ({score.failed_submits} attempts)",
        )

    status_title = (
        "[bold red]Session Revealed (Score 0)[/bold red]"
        if score.revealed
        else "[bold green]Session Completed[/bold green]"
    )

    score_text = f"[bold cyan]{score.total_score} / {score.max_possible} pts[/bold cyan]"
    header_text = f"{status_title}  |  [bold]Final Score:[/bold] {score_text}"

    elements: list[Any] = [
        Text.from_markup(header_text),
        Text(""),
        breakdown_table,
        Text(""),
        Text.from_markup(f"[bold]Config Drift Evaluation:[/bold] {drift.summary}"),
    ]

    if feedback:
        elements.extend([Text(""), Text.from_markup(f"[bold]Mentor Feedback:[/bold] {feedback}")])

    if root_cause:
        elements.extend([Text(""), Text.from_markup(f"[bold]Root Cause:[/bold] {root_cause}")])

    return Panel(
        Group(*elements),
        title="[bold green]RESULTS & SCORECARD[/bold green]",
        border_style="green",
        padding=(1, 2),
    )


def render_check_results(results: list[CheckResult]) -> Table:
    """Render a Rich Table of verification check results with PASS/FAIL badges."""
    table = Table(title="Verification Check Results", show_lines=True)
    table.add_column("Check ID", style="bold cyan")
    table.add_column("Status", justify="center")
    table.add_column("Expected")
    table.add_column("Observed")
    table.add_column("Message")

    for r in results:
        status_badge = "[bold green]PASS[/bold green]" if r.passed else "[bold red]FAIL[/bold red]"
        table.add_row(
            r.check_id,
            status_badge,
            r.expected,
            r.observed,
            r.message or "",
        )
    return table


def render_history_table(
    history: list[dict[str, Any]],
    stats: dict[str, Any] | None = None,
) -> Table:
    """Render a summary table of past troubleshooting sessions."""
    table = Table(title="Session History", show_lines=True)
    table.add_column("Session ID", justify="right")
    table.add_column("Fault ID", style="bold cyan")
    table.add_column("Level", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Score", justify="right")
    table.add_column("Time", justify="right")
    table.add_column("Hints", justify="center")
    table.add_column("Submits", justify="center")
    table.add_column("Date", style="dim")

    for s in history:
        status = s.get("status", "")
        if status == "SOLVED":
            status_fmt = "[bold green]SOLVED[/bold green]"
        elif status == "REVEALED":
            status_fmt = "[bold yellow]REVEALED[/bold yellow]"
        elif status == "ABANDONED":
            status_fmt = "[bold red]ABANDONED[/bold red]"
        else:
            status_fmt = status

        score_val = s.get("final_score")
        score_str = f"{score_val}" if score_val is not None else "—"
        sec_val = s.get("seconds")
        time_str = f"{sec_val}s" if sec_val is not None else "—"

        table.add_row(
            str(s.get("id", "")),
            str(s.get("fault_id", "")),
            str(s.get("level", "")),
            status_fmt,
            score_str,
            time_str,
            str(s.get("hints_used", 0)),
            str(s.get("failed_submits", 0)),
            str(s.get("started_at", ""))[:19],
        )

    if stats and stats.get("total_sessions", 0) > 0:
        table.caption = (
            f"Total Sessions: {stats['total_sessions']}  |  "
            f"Solved: {stats['solved_count']}  |  "
            f"Avg Score: {stats['average_score']} pts  |  "
            f"Avg Time: {stats['average_seconds']}s"
        )

    return table
