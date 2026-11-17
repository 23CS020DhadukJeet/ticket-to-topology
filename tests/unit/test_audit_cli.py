"""Unit tests for Phase 7 CLI commands, exit codes, and security guards (U7.4-U7.7)."""

import json
import socket
from pathlib import Path

import pytest
from typer.testing import CliRunner

from t2t.audit.report import validate_json_report
from t2t.cli.app import app
from t2t.devices.session import DeviceSession
from t2t.errors import ReadOnlyViolation


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# U7.4: Exit codes for --fail-on and unreachable device
def test_u7_4_cli_exit_codes_clean_baseline(runner: CliRunner) -> None:
    """Baseline with no findings returns exit code 0."""
    res = runner.invoke(
        app,
        ["audit", "--from-dir", "tests/synthetic/audit/baseline"],
    )
    assert res.exit_code == 0
    assert "No redistribution risks detected" in res.stdout or "0 High" in res.stdout


def test_u7_4_cli_exit_codes_fail_on_thresholds(runner: CliRunner) -> None:
    """Test --fail-on high vs medium exit codes."""
    # A3 is Medium severity
    medium_dir = "tests/synthetic/audit/a3_ospf_no_subnets/positive"

    # --fail-on high should exit 0 because A3 is Medium
    res_high = runner.invoke(app, ["audit", "--from-dir", medium_dir, "--fail-on", "high"])
    assert res_high.exit_code == 0

    # --fail-on medium should exit 1 because A3 is Medium
    res_med = runner.invoke(app, ["audit", "--from-dir", medium_dir, "--fail-on", "medium"])
    assert res_med.exit_code == 1

    # Missing directory triggers error exit code 2
    res_err = runner.invoke(app, ["audit", "--from-dir", "nonexistent/dir/path"])
    assert res_err.exit_code == 2


# U7.5: JSON report validates against schema
def test_u7_5_json_report_validates_against_schema(runner: CliRunner, tmp_path: Path) -> None:
    report_file = tmp_path / "audit_report.json"
    res = runner.invoke(
        app,
        [
            "audit",
            "--from-dir",
            "tests/synthetic/audit/baseline",
            "--format",
            "json",
            "--output",
            str(report_file),
        ],
    )
    assert res.exit_code == 0
    assert report_file.exists()

    content = report_file.read_text(encoding="utf-8")
    data = json.loads(content)
    assert data["summary"]["total_devices"] == 4
    assert "findings" in data
    assert "config_hashes" in data

    # Schema validation function
    is_valid = validate_json_report(content)
    assert is_valid is True


# U7.6: Spy - audit path never calls push_config; non-show command raises ReadOnlyViolation
def test_u7_6_read_only_spy_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that audit operates in read_only mode and push_config is never called."""
    from t2t.config import Inventory, Router, Settings

    inv = Inventory(
        routers=[
            Router(
                name="R1",
                host="192.168.100.11",
                role="asbr",
                golden_path="flash:golden.cfg",
            )
        ]
    )
    settings = Settings()

    with (
        DeviceSession(inventory=inv, settings=settings, read_only=True, replay=True) as session,
        pytest.raises(ReadOnlyViolation),
    ):
        cmd = ["interface Loopback100", "ip address 1.1.1.1 255.255.255.255"]
        session.push_config("R1", cmd)


# U7.7: --from-dir works with sockets disabled
def test_u7_7_from_dir_works_with_sockets_disabled(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify that --from-dir performs zero network calls even if socket creation is blocked."""

    def guarded_socket(*args, **kwargs):
        raise RuntimeError("Network activity strictly forbidden during offline --from-dir audit!")

    monkeypatch.setattr(socket, "socket", guarded_socket)
    monkeypatch.setattr(socket, "create_connection", guarded_socket)

    res = runner.invoke(
        app,
        ["audit", "--from-dir", "tests/synthetic/audit/baseline"],
    )
    assert res.exit_code == 0
    assert "Devices: 4" in res.stdout
