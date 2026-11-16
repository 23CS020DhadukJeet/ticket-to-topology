"""Unit tests for DeviceSession."""

from pathlib import Path

import pytest

from t2t.config import Inventory, Router
from t2t.devices.session import DeviceSession
from t2t.errors import DeviceUnreachable, ReadOnlyViolation


def test_session_replay_mode(tmp_path: Path) -> None:
    """Verify DeviceSession in replay mode creates MockDevices and records commands."""
    fixtures_dir = tmp_path / "fixtures"
    baseline_r1 = fixtures_dir / "baseline" / "R1"
    baseline_r1.mkdir(parents=True)
    (baseline_r1 / "show_version.txt").write_text("Cisco IOS XE Version 17.3\n", encoding="utf-8")

    inventory = Inventory(routers=[Router(name="R1", host="192.168.100.11", role="branch")])

    with DeviceSession(
        inventory=inventory,
        replay=True,
        fixtures_root=fixtures_dir,
    ) as session:
        out = session.show("R1", "show version")
        assert "Version 17.3" in out

        session.push_config(
            "R1", ["interface Loopback0", "ip address 1.1.1.1 255.255.255.255"], reason="test"
        )

        # Verify command log
        log = session.command_log
        assert len(log) == 3
        assert log[0][1] == "R1" and log[0][2] == "show"
        assert log[1][2] == "config" and "Loopback0" in log[1][3]
        assert log[2][2] == "config" and "1.1.1.1" in log[2][3]

        with pytest.raises(DeviceUnreachable, match="Router 'R99' not configured"):
            session.get_device("R99")


def test_session_read_only_blocks_push_config(tmp_path: Path) -> None:
    """Verify DeviceSession read_only flag blocks push_config."""
    inventory = Inventory(routers=[Router(name="R1", host="192.168.100.11", role="branch")])

    with (
        DeviceSession(
            inventory=inventory,
            read_only=True,
            replay=True,
            fixtures_root=tmp_path,
        ) as session,
        pytest.raises(ReadOnlyViolation, match="Session is in read_only mode"),
    ):
        session.push_config("R1", ["interface Loopback0"])
