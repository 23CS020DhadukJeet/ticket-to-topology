"""Unit tests U2.2 - U2.5 for Phase 2 device layer."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from netmiko.exceptions import NetmikoTimeoutException

from t2t.clock import FakeClock
from t2t.config import Router, Settings
from t2t.devices.mock_device import MockDevice
from t2t.devices.netmiko_device import NetmikoDevice
from t2t.errors import DeviceUnreachable, FixtureMissing, ReadOnlyViolation


def test_u2_2_mock_device_returns_fixture_or_raises(tmp_path: Path) -> None:
    """U2.2: MockDevice returns fixture content when present, raises FixtureMissing when absent."""
    # Setup fake fixture structure
    baseline_r1 = tmp_path / "baseline" / "R1"
    baseline_r1.mkdir(parents=True)
    (baseline_r1 / "show_version.txt").write_text(
        "Cisco IOS XE Software, Version 17.09.04a\n", encoding="utf-8"
    )

    device = MockDevice(name="R1", fixtures_root=tmp_path, scenario="baseline")
    output = device.send_show("show version")
    assert "Version 17.09.04a" in output

    with pytest.raises(FixtureMissing, match="Fixture missing"):
        device.send_show("show ip route 192.168.1.1")


def test_u2_3_read_only_rejects_config_and_allows_show() -> None:
    """U2.3: read_only rejects write, copy, delete, reload; allows show."""
    clock = FakeClock()
    device = NetmikoDevice(
        name="R1",
        host="192.168.100.11",
        username="admin",
        password="secretpassword",  # noqa: S106  # pragma: allowlist secret
        device_type="cisco_xe",
        read_only=True,
        clock=clock,
    )

    forbidden = [
        "configure terminal",
        "conf t",
        "write memory",
        "write",
        "copy running-config startup-config",
        "delete flash:test",
        "reload",
        "erase startup-config",
    ]

    for cmd in forbidden:
        with pytest.raises(ReadOnlyViolation, match="Read-only violation"):
            device.send_show(cmd)

    with pytest.raises(ReadOnlyViolation, match="Read-only violation"):
        device.push_config(["interface Loopback0", "description TEST"])


def test_u2_4_retry_connect_backoff_and_failure() -> None:
    """U2.4: patched connect fails twice then succeeds; 4th failure raises DeviceUnreachable."""
    clock = FakeClock()
    device = NetmikoDevice(
        name="R1",
        host="192.168.100.11",
        username="admin",
        password="password",  # noqa: S106  # pragma: allowlist secret
        device_type="cisco_xe",
        clock=clock,
    )

    # 1. Connect fails twice, succeeds on 3rd attempt
    mock_conn_instance = MagicMock()

    with patch(
        "t2t.devices.netmiko_device.ConnectHandler",
        side_effect=[
            NetmikoTimeoutException("Timeout 1"),
            NetmikoTimeoutException("Timeout 2"),
            mock_conn_instance,
        ],
    ) as patched:
        conn = device._connect()
        assert conn == mock_conn_instance
        assert patched.call_count == 3
        # Clock advanced for backoff (1s + 3s = 4s)
        assert clock.now() >= 4.0

    # 2. Connect fails 3 times -> raises DeviceUnreachable
    clock_fail = FakeClock()
    device_fail = NetmikoDevice(
        name="R1",
        host="192.168.100.11",
        username="admin",
        password="password",  # noqa: S106  # pragma: allowlist secret
        device_type="cisco_xe",
        clock=clock_fail,
    )

    with patch(
        "t2t.devices.netmiko_device.ConnectHandler",
        side_effect=NetmikoTimeoutException("Persistent timeout"),
    ) as patched_fail:
        with pytest.raises(DeviceUnreachable, match="Device R1 unreachable"):
            device_fail._connect()
        assert patched_fail.call_count == 3


def test_u2_5_repr_and_logs_never_contain_password() -> None:
    """U2.5: repr and logs of config never contain the raw password."""
    secret_pass = "Sup3rS3cr3tP@ssw0rd!"  # noqa: S105  # pragma: allowlist secret
    settings = Settings(lab_password=secret_pass)  # type: ignore[arg-type]

    # SecretStr protects representation
    assert secret_pass not in repr(settings)
    assert secret_pass not in str(settings)
    assert settings.lab_password.get_secret_value() == secret_pass

    # Check Router model
    router = Router(name="R1", host="192.168.100.11", role="branch")
    assert secret_pass not in repr(router)
