"""Unit tests for doctor and status CLI commands."""

from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from t2t.cli.app import app


def test_doctor_replay_mode(tmp_path: Path, monkeypatch: Any) -> None:
    """Verify t2t doctor --replay runs against fixtures."""
    fixtures_dir = tmp_path / "fixtures"
    for r in ["R1", "R2", "R3", "R4"]:
        r_dir = fixtures_dir / "baseline" / r
        r_dir.mkdir(parents=True)
        (r_dir / "show_version.txt").write_text(
            "Cisco IOS XE Software, Version 17.09.04a\n", encoding="utf-8"
        )
        (r_dir / "dir_flash_golden_cfg.txt").write_text(
            "1234  -rw-  golden.cfg\n", encoding="utf-8"
        )
        (r_dir / "show_running_config_section_archive.txt").write_text(
            "archive\n path flash:archive\n", encoding="utf-8"
        )
        (r_dir / "show_vrf.txt").write_text("MGMT  1:1  ipv4,ipv6\n", encoding="utf-8")

    runner = CliRunner()
    with monkeypatch.context() as m:
        m.setattr(
            "t2t.cli.app.DeviceSession",
            lambda **kwargs: __import__(
                "t2t.devices.session", fromlist=["DeviceSession"]
            ).DeviceSession(fixtures_root=fixtures_dir, **kwargs),
        )
        result = runner.invoke(app, ["doctor", "--replay"])
        assert "Lab Environment Doctor Check" in result.output
        assert "PASS" in result.output
        assert result.exit_code == 0


def test_status_command(tmp_path: Path, monkeypatch: Any) -> None:
    """Verify t2t status --replay renders rich table with routes and MISSING."""
    fixtures_dir = tmp_path / "fixtures"
    # Create fixture for R1 10.10.1.0/24
    r1_dir = fixtures_dir / "baseline" / "R1"
    r1_dir.mkdir(parents=True)
    (r1_dir / "show_ip_route_10_10_1_0_255_255_255_0.txt").write_text(
        'Routing entry for 10.10.1.0/24\n  Known via "eigrp 100", distance 90, metric 1308160\n'
        "  * 10.1.12.1, via GigabitEthernet2\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    with monkeypatch.context() as m:
        m.setattr(
            "t2t.cli.app.DeviceSession",
            lambda **kwargs: __import__(
                "t2t.devices.session", fromlist=["DeviceSession"]
            ).DeviceSession(fixtures_root=fixtures_dir, **kwargs),
        )
        result = runner.invoke(app, ["status", "--replay"])
        assert "Redistribution Status: Key Prefixes" in result.output
        assert "EIGRP (90)" in result.output
        assert "MISSING" in result.output
        assert result.exit_code == 0


def test_reset_command_replay(monkeypatch: Any) -> None:
    """Verify t2t reset --replay --force restores baseline."""
    runner = CliRunner()
    with monkeypatch.context() as m:
        m.setattr("t2t.cli.app.load_baseline_checks", lambda path: [])
        result = runner.invoke(app, ["reset", "--replay", "--force"])
        assert "Lab Reset Results" in result.output
        assert result.exit_code == 0


def test_reveal_command_no_active_fault() -> None:
    """Verify t2t reveal informs user when no fault is active."""
    runner = CliRunner()
    result = runner.invoke(app, ["reveal"])
    assert "No fault is currently active" in result.output
    assert result.exit_code == 0


def test_qualify_command_requires_args() -> None:
    """Verify t2t qualify requires either --fault or --all."""
    runner = CliRunner()
    result = runner.invoke(app, ["qualify"])
    assert "Specify either --fault <ID> or --all" in result.output
    assert result.exit_code == 1
