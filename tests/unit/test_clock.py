"""Unit tests for injectable Clock."""

import pytest

from t2t.clock import FakeClock, SystemClock


def test_fake_clock() -> None:
    """Verify FakeClock advances time without real sleeping."""
    clock = FakeClock(start_time=100.0)
    assert clock.now() == 100.0

    clock.sleep(5.5)
    assert clock.now() == 105.5
    assert clock.sleep_calls == [5.5]

    with pytest.raises(ValueError, match="Cannot sleep negative"):
        clock.sleep(-1.0)


def test_system_clock() -> None:
    """Verify SystemClock returns real time."""
    clock = SystemClock()
    t1 = clock.now()
    clock.sleep(0.01)
    t2 = clock.now()
    assert t2 >= t1
