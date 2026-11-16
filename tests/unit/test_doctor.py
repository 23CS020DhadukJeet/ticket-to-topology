"""Unit tests for the doctor CLI command."""

from pathlib import Path

from typer.testing import CliRunner

from t2t.cli.app import app


def test_doctor_replay_mode(tmp_path: Path, monkeypatch) -> None:
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
    # Mock DeviceSession fixtures_root
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
