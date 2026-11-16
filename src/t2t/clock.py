"""Injectable clock abstraction to eliminate arbitrary time.sleep calls."""

import time
from typing import Protocol


class Clock(Protocol):
    """Protocol for time and sleeping operations."""

    def now(self) -> float:
        """Return current timestamp in seconds."""
        ...

    def sleep(self, seconds: float) -> None:
        """Sleep or advance time by seconds."""
        ...


class SystemClock:
    """Real system clock using Python's standard time module."""

    def now(self) -> float:
        """Return current real timestamp."""
        return time.time()

    def sleep(self, seconds: float) -> None:
        """Perform actual system sleep."""
        time.sleep(seconds)


class FakeClock:
    """Deterministic simulated clock for tests and fast-forwarding."""

    def __init__(self, start_time: float = 0.0) -> None:
        self._current_time: float = start_time
        self.sleep_calls: list[float] = []

    def now(self) -> float:
        """Return current simulated timestamp."""
        return self._current_time

    def sleep(self, seconds: float) -> None:
        """Advance simulated time without blocking."""
        if seconds < 0:
            raise ValueError("Cannot sleep negative time")
        self._current_time += seconds
        self.sleep_calls.append(seconds)
