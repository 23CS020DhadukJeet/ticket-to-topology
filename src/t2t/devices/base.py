"""Base Device Protocol interface."""

from typing import Protocol


class Device(Protocol):
    """Protocol representing a managed or simulated network device."""

    name: str

    def send_show(self, command: str) -> str:
        """Send a show command and return raw output text."""
        ...

    def push_config(self, commands: list[str]) -> str:
        """Push configuration commands and return device response."""
        ...

    def close(self) -> None:
        """Close connection and clean up resources."""
        ...
