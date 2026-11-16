"""Unit tests for wait_for_settle and wait_for_baseline using Clock (U4.3)."""

from unittest.mock import MagicMock

import pytest

from t2t.clock import FakeClock
from t2t.config import Inventory, Router
from t2t.errors import T2TError
from t2t.models import Check


@pytest.fixture
def test_inventory() -> Inventory:
    """Fixture providing a standard test inventory."""
    return Inventory(
        defaults={"device_type": "cisco_xe"},
        routers=[
            Router(name="R1", host="192.168.100.11", role="branch"),
            Router(name="R2", host="192.168.100.12", role="asbr"),
        ],
    )


def test_u4_3_wait_for_settle_converges(test_inventory: Inventory) -> None:
    """U4.3: Settle completes after 3 identical consecutive polls with FakeClock."""
    from t2t.faults.settle import wait_for_settle

    clock = FakeClock()
    session = MagicMock()
    # Return constant output for show commands
    session.show.return_value = "constant output"

    settled = wait_for_settle(
        session=session,
        clock=clock,
        inventory=test_inventory,
        stable_polls=3,
        poll_interval=5.0,
        timeout=60.0,
    )
    assert settled is True
    assert clock.now() >= 10.0  # Polled at least 2 intervals


def test_u4_3_wait_for_settle_timeout_returns_warning(test_inventory: Inventory) -> None:
    """U4.3: Settle times out and returns False / logs warning on flapping outputs."""
    from t2t.faults.settle import wait_for_settle

    clock = FakeClock()
    session = MagicMock()

    # Alternate output to simulate continuous flapping
    def flapping_show(router: str, cmd: str) -> str:
        return f"output at time {clock.now()}"

    session.show.side_effect = flapping_show

    settled = wait_for_settle(
        session=session,
        clock=clock,
        inventory=test_inventory,
        stable_polls=3,
        poll_interval=5.0,
        timeout=20.0,
    )
    assert settled is False
    assert clock.now() >= 20.0


def test_u4_3_wait_for_baseline_timeout_raises(test_inventory: Inventory) -> None:
    """U4.3: wait_for_baseline raises T2TError on timeout with failing checks."""
    from t2t.faults.settle import wait_for_baseline

    clock = FakeClock()
    session = MagicMock()
    # Route not in table -> check will fail
    session.show.return_value = "% Network not in table\n"

    check = Check(
        id="b_test",
        kind="route_present",
        router="R1",
        prefix="10.10.1.0/24",
        params={"protocol": "eigrp"},
    )

    with pytest.raises(T2TError, match="baseline.*timeout|b_test"):
        wait_for_baseline(
            session=session,
            clock=clock,
            baseline_checks=[check],
            timeout=10.0,
            poll_interval=5.0,
        )
