"""Netmiko-backed device implementation.

NOTE: Per AGENTS.md Hard Rule 1, this is the ONLY file in src/ that may import netmiko.
"""

from typing import Any

from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoBaseException,
    NetmikoTimeoutException,
)

from t2t.clock import Clock, SystemClock
from t2t.errors import AuthFailed, DeviceUnreachable, ReadOnlyViolation


class NetmikoDevice:
    """Network device connection managed by Netmiko."""

    def __init__(
        self,
        name: str,
        host: str,
        username: str,
        password: str,
        device_type: str = "cisco_xe",
        conn_timeout: int = 15,
        auth_timeout: int = 15,
        banner_timeout: int = 15,
        read_timeout: float = 30.0,
        read_only: bool = False,
        clock: Clock | None = None,
        strict_host_keys: bool = False,
    ) -> None:
        self.name = name
        self.host = host
        self.username = username
        self.password = password
        self.device_type = device_type
        self.conn_timeout = conn_timeout
        self.auth_timeout = auth_timeout
        self.banner_timeout = banner_timeout
        self.read_timeout = read_timeout
        self.read_only = read_only
        self.clock: Clock = clock if clock is not None else SystemClock()
        self.strict_host_keys = strict_host_keys
        self._connection: Any = None

    def _connect(self) -> Any:
        """Establish Netmiko connection with 3 attempts and backoff."""
        if self._connection is not None:
            return self._connection

        backoffs = [1.0, 3.0]
        attempts = 3

        for attempt in range(1, attempts + 1):
            try:
                connect_kwargs: dict[str, Any] = {
                    "device_type": self.device_type,
                    "host": self.host,
                    "username": self.username,
                    "password": self.password,
                    "conn_timeout": self.conn_timeout,
                    "auth_timeout": self.auth_timeout,
                    "banner_timeout": self.banner_timeout,
                }
                if self.strict_host_keys:
                    connect_kwargs["system_host_keys"] = True
                    connect_kwargs["ssh_strict"] = True

                conn = ConnectHandler(**connect_kwargs)
                self._connection = conn
                return conn
            except NetmikoAuthenticationException as err:
                raise AuthFailed(
                    f"Authentication failed for {self.name} ({self.host}): {err}"
                ) from err
            except (NetmikoTimeoutException, NetmikoBaseException, OSError) as err:
                if attempt == attempts:
                    msg = (
                        f"Device {self.name} unreachable ({self.host}) "
                        f"after {attempts} attempts: {err}"
                    )
                    raise DeviceUnreachable(msg) from err
                sleep_time = backoffs[attempt - 1] if attempt - 1 < len(backoffs) else 3.0
                self.clock.sleep(sleep_time)

    def send_show(self, command: str) -> str:
        """Send a show command and return the raw string output.

        If read_only is True, rejects any command not beginning with 'show '.
        """
        trimmed = command.strip()
        if self.read_only and not trimmed.startswith("show "):
            raise ReadOnlyViolation(
                f"Read-only violation on {self.name}: command '{command}' is not a show command."
            )

        conn = self._connect()
        output: str = conn.send_command(command, read_timeout=self.read_timeout)
        return output

    def push_config(self, commands: list[str]) -> str:
        """Push configuration commands to the device.

        If read_only is True, raises ReadOnlyViolation before connecting.
        """
        if self.read_only:
            raise ReadOnlyViolation(
                f"Read-only violation on {self.name}: cannot push config to read-only device."
            )

        conn = self._connect()

        # Handle 'configure replace' via send_command_timing if requested
        if len(commands) == 1 and commands[0].strip().startswith("configure replace"):
            replace_cmd = commands[0].strip()
            # configure replace takes longer
            output: str = conn.send_command_timing(replace_cmd, read_timeout=120.0)
            if "confirm" in output.lower():
                output += conn.send_command_timing("y", read_timeout=60.0)
            return output

        output = conn.send_config_set(commands, read_timeout=self.read_timeout)
        return str(output)

    def close(self) -> None:
        """Disconnect Netmiko session."""
        if self._connection is not None:
            try:
                self._connection.disconnect()
            except Exception:  # noqa: S110
                pass
            finally:
                self._connection = None

    def __enter__(self) -> "NetmikoDevice":
        self._connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
