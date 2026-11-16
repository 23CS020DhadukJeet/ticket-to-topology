"""Custom exception hierarchy for Ticket-to-Topology (t2t)."""


class T2TError(Exception):
    """Base exception for all t2t application errors."""

    exit_code: int = 1

    def __init__(self, message: str, exit_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if exit_code is not None:
            self.exit_code = exit_code


class DeviceUnreachable(T2TError):
    """Device could not be reached over network/SSH."""

    exit_code = 10


class AuthFailed(T2TError):
    """Authentication or credential rejection on device."""

    exit_code = 11


class FixtureMissing(T2TError):
    """Fixture required for offline replay does not exist."""

    exit_code = 12


class FaultInvalid(T2TError):
    """Fault definition or syntax in catalog YAML is invalid."""

    exit_code = 13


class AIUnavailable(T2TError):
    """Configured AI provider is down, timed out, or unconfigured."""

    exit_code = 14


class StateCorrupt(T2TError):
    """Database or session state store is corrupted."""

    exit_code = 15


class ReadOnlyViolation(T2TError):
    """Attempted configuration push or non-show command on a read-only device."""

    exit_code = 16
