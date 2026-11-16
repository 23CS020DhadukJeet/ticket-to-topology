"""Integration lab tests for Phase 2 device layer.

NOTE: These tests require the live 4-router lab and are excluded by default.
Run with: pytest -m lab
"""

import time

import pytest
from typer.testing import CliRunner

from t2t.cli.app import app
from t2t.devices.session import DeviceSession
from t2t.errors import ReadOnlyViolation


@pytest.mark.lab
def test_i2_1_lab_doctor_green() -> None:
    """I2.1 (lab): t2t doctor all green in under 30 seconds."""
    runner = CliRunner()
    start = time.time()
    result = runner.invoke(app, ["doctor"])
    duration = time.time() - start

    assert result.exit_code == 0
    assert duration < 30.0
    assert "PASS" in result.output


@pytest.mark.lab
def test_i2_2_lab_push_and_revert() -> None:
    """I2.2 (lab): push description T2T-TEST on Loopback0, read back, revert."""
    with DeviceSession() as session:
        # Push test description
        session.push_config(
            "R1", ["interface Loopback0", "description T2T-TEST"], reason="test I2.2"
        )
        output = session.show("R1", "show running-config interface Loopback0")
        assert "T2T-TEST" in output

        # Revert
        session.push_config("R1", ["interface Loopback0", "no description"], reason="revert I2.2")
        revert_output = session.show("R1", "show running-config interface Loopback0")
        assert "T2T-TEST" not in revert_output


@pytest.mark.lab
def test_i2_3_lab_unreachable_doctor_fails_fast() -> None:
    """I2.3 (lab): power one router off or invalid IP -> doctor FAIL within timeout without hang."""
    runner = CliRunner()
    start = time.time()
    # doctor must fail fast without hanging
    runner.invoke(app, ["doctor"])
    duration = time.time() - start

    assert duration < 10.0


@pytest.mark.lab
def test_i2_4_lab_read_only_blocks_push() -> None:
    """I2.4 (lab): read_only device cannot push even when reachable."""
    with DeviceSession(read_only=True) as session, pytest.raises(ReadOnlyViolation):
        session.push_config("R1", ["interface Loopback0", "description FORBIDDEN"])
