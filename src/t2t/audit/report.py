"""Report generators and JSON schema validator for audit findings."""

import json
import re
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from rich.table import Table

from t2t.audit.rules import Finding


def get_tool_version() -> str:
    """Retrieve package version or fallback."""
    try:
        return version("ticket-to-topology")
    except PackageNotFoundError:
        return "0.1.0"


SCHEMA_PATH = Path(__file__).parent / "report.schema.json"


class AuditReport:
    """Container for audit findings, device hashes, and summary metrics."""

    def __init__(
        self,
        device_list: list[str],
        config_hashes: dict[str, str],
        findings: list[Finding],
        fail_on: str = "medium",
        timestamp: str | None = None,
        tool_version: str | None = None,
    ) -> None:
        self.device_list = device_list
        self.config_hashes = config_hashes
        self.findings = findings
        self.fail_on = fail_on.lower()
        self.timestamp = timestamp or datetime.now(UTC).isoformat()
        self.version = tool_version or get_tool_version()

        self.high_count = sum(1 for f in findings if f.severity == "High")
        self.medium_count = sum(1 for f in findings if f.severity == "Medium")
        self.low_count = sum(1 for f in findings if f.severity == "Low")

        # Determine pass/fail based on fail_on threshold
        if self.fail_on == "high":
            self.passed = self.high_count == 0
        else:
            self.passed = (self.high_count + self.medium_count) == 0

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary matching report.schema.json."""
        return {
            "timestamp": self.timestamp,
            "version": self.version,
            "device_list": self.device_list,
            "config_hashes": self.config_hashes,
            "findings": [f.model_dump() for f in self.findings],
            "summary": {
                "total_devices": len(self.device_list),
                "high_count": self.high_count,
                "medium_count": self.medium_count,
                "low_count": self.low_count,
                "passed": self.passed,
            },
        }


def render_table(report: AuditReport) -> Table:
    """Render audit findings as a Rich terminal table."""
    table = Table(
        title=f"Configuration Audit Report (Devices: {len(report.device_list)})",
        show_lines=True,
    )
    table.add_column("Rule", style="bold cyan", width=6, justify="center")
    table.add_column("Severity", justify="center", width=10)
    table.add_column("Device", style="bold", width=12)
    table.add_column("Message & Remediation", style="white")

    if not report.findings:
        table.add_row(
            "OK",
            "[bold green]PASS[/bold green]",
            "All",
            "No redistribution risks detected. Configurations comply with all audit rules.",
        )
        return table

    for f in report.findings:
        if f.severity == "High":
            sev_badge = "[bold white on red] HIGH [/bold white on red]"
        elif f.severity == "Medium":
            sev_badge = "[bold black on yellow] MEDIUM [/bold black on yellow]"
        else:
            sev_badge = "[bold black on cyan] LOW [/bold black on cyan]"

        msg_body = (
            f"[bold]{f.message}[/bold]\n"
            f"[yellow]Remediation:[/yellow] {f.remediation}\n"
            f"[dim]Topic: {f.exam_topic}[/dim]"
        )
        table.add_row(f.rule_id, sev_badge, f.device, msg_body)

    return table


def render_json(report: AuditReport) -> str:
    """Render audit report as formatted JSON."""
    return json.dumps(report.to_dict(), indent=2)


def render_markdown(report: AuditReport) -> str:
    """Render audit report as GitHub Flavored Markdown."""
    lines: list[str] = [
        "# Network Redistribution Configuration Audit Report",
        "",
        f"- **Timestamp:** `{report.timestamp}`",
        f"- **Tool Version:** `{report.version}`",
        f"- **Devices Audited ({len(report.device_list)}):** {', '.join(report.device_list)}",
        f"- **Status:** {'**PASS**' if report.passed else '**FAIL**'}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| High Severity Findings | {report.high_count} |",
        f"| Medium Severity Findings | {report.medium_count} |",
        f"| Low Severity Findings | {report.low_count} |",
        (
            f"| Compliance Gate | "
            f"{'PASS' if report.passed else f'FAIL (Threshold: {report.fail_on})'} |"
        ),
        "",
        "## Configuration Checksums",
        "",
        "| Device | SHA-256 Hash |",
        "|---|---|",
    ]

    for dev, sha in sorted(report.config_hashes.items()):
        lines.append(f"| {dev} | `{sha}` |")

    lines.extend(["", "## Findings Detail", ""])
    if not report.findings:
        lines.append("No configuration risks detected. All audit checks passed.")
    else:
        for idx, f in enumerate(report.findings, start=1):
            lines.extend(
                [
                    f"### {idx}. [{f.rule_id}] {f.severity.upper()} — {f.device}",
                    f"- **Rule ID:** `{f.rule_id}`",
                    f"- **Severity:** **{f.severity}**",
                    f"- **Device(s):** `{f.device}`",
                    f"- **Exam Topic:** *{f.exam_topic}*",
                    "",
                    "**Issue:**",
                    f"> {f.message}",
                    "",
                    "**Remediation:**",
                    "```cisco",
                    f"{f.remediation}",
                    "```",
                    "",
                ]
            )

    return "\n".join(lines)


def validate_json_report(json_str: str) -> bool:
    """Validate a JSON audit report string against report.schema.json."""
    try:
        data = json.loads(json_str)
        if not isinstance(data, dict):
            return False

        # Load stored schema
        if not SCHEMA_PATH.exists():
            return False
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

        # Verify required root fields
        for field in schema.get("required", []):
            if field not in data:
                return False

        # Verify summary required fields
        summary = data.get("summary")
        if not isinstance(summary, dict):
            return False
        for sfield in ["total_devices", "high_count", "medium_count", "low_count", "passed"]:
            if sfield not in summary:
                return False

        # Verify config_hashes hex format
        hashes = data.get("config_hashes")
        if not isinstance(hashes, dict):
            return False
        hex_pattern = re.compile(r"^[a-f0-9]{64}$")
        for h in hashes.values():
            if not isinstance(h, str) or not hex_pattern.match(h):
                return False

        # Verify findings list structure
        findings = data.get("findings")
        if not isinstance(findings, list):
            return False
        for f in findings:
            if not isinstance(f, dict):
                return False
            for req in ["rule_id", "severity", "device", "message", "remediation", "exam_topic"]:
                if req not in f:
                    return False
            if f.get("severity") not in ("High", "Medium", "Low"):
                return False

        return True
    except Exception:
        return False
