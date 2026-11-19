"""Device session manager orchestrating all router interactions."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from t2t.clock import Clock, FakeClock, SystemClock
from t2t.config import Inventory, Settings, load_inventory, load_settings
from t2t.devices.base import Device
from t2t.devices.mock_device import MockDevice
from t2t.devices.netmiko_device import NetmikoDevice
from t2t.errors import DeviceUnreachable, ReadOnlyViolation


class DeviceSession:
    """Manages connections to all lab routers during an execution session.

    Per AGENTS.md Rule 4:
    All device configuration changes go through DeviceSession.push_config.
    Audit code uses read_only devices and never calls push_config.
    """

    def __init__(
        self,
        inventory: Inventory | None = None,
        settings: Settings | None = None,
        read_only: bool = False,
        replay: bool = False,
        scenario: str = "baseline",
        fixtures_root: Path = Path("tests/fixtures"),
        clock: Clock | None = None,
        strict_host_keys: bool = False,
    ) -> None:
        self.settings = settings or load_settings()
        self.inventory = inventory or load_inventory(self.settings.t2t_inventory)
        self.read_only = read_only
        self.replay = replay
        self.scenario = scenario
        if fixtures_root == Path("tests/fixtures") and not fixtures_root.exists():
            pkg_demo = Path(__file__).resolve().parent.parent / "demo_data"
            if pkg_demo.exists():
                fixtures_root = pkg_demo
        self.fixtures_root = fixtures_root
        self.strict_host_keys = strict_host_keys
        if clock is not None:
            self.clock = clock
        elif replay:
            self.clock = FakeClock()
        else:
            self.clock = SystemClock()

        self.devices: dict[str, Device] = {}
        self.command_log: list[tuple[float, str, str, str]] = []
        self._initialize_devices()

    def _initialize_devices(self) -> None:
        """Instantiate mock or real devices for all routers in inventory."""
        defaults = self.inventory.defaults

        for router in self.inventory.routers:
            if self.replay:
                self.devices[router.name] = MockDevice(
                    name=router.name,
                    fixtures_root=self.fixtures_root,
                    scenario=self.scenario,
                )
            else:
                device_type = router.device_type or defaults.get("device_type", "cisco_xe")
                self.devices[router.name] = NetmikoDevice(
                    name=router.name,
                    host=router.host,
                    username=self.settings.lab_username,
                    password=self.settings.lab_password.get_secret_value(),
                    device_type=device_type,
                    read_only=self.read_only,
                    clock=self.clock,
                    strict_host_keys=self.strict_host_keys,
                )

    def get_device(self, router_name: str) -> Device:
        """Retrieve a managed device by name."""
        if router_name not in self.devices:
            raise DeviceUnreachable(f"Router '{router_name}' not configured in inventory.")
        return self.devices[router_name]

    def show(self, router: str, cmd: str) -> str:
        """Execute a show command and record in command_log."""
        dev = self.get_device(router)
        ts = self.clock.now()
        output = dev.send_show(cmd)
        self.command_log.append((ts, router, "show", cmd))
        return output

    def push_config(self, router: str, commands: Sequence[str], reason: str = "") -> str:
        """Push configuration to a router and record in command_log.

        Per AGENTS.md Rule 4:
        This is the ONLY approved path for device configuration changes.
        """
        if self.read_only:
            msg = (
                f"Session is in read_only mode. "
                f"Cannot push configuration to {router} (reason: '{reason}')."
            )
            raise ReadOnlyViolation(msg)

        dev = self.get_device(router)
        ts = self.clock.now()
        output = dev.push_config(list(commands))
        for cmd in commands:
            self.command_log.append((ts, router, "config", cmd))
        return output

    def close(self) -> None:
        """Close all device connections."""
        for dev in self.devices.values():
            dev.close()

    def __enter__(self) -> "DeviceSession":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
