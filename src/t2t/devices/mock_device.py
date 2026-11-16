"""Mock device implementation for deterministic offline replay and CI testing."""

import ipaddress
import re
from pathlib import Path

from t2t.devices.slug import slug
from t2t.errors import FixtureMissing


def _candidate_slugs(command: str) -> list[str]:
    """Return primary slug and any protocol-equivalent alternative slugs."""
    primary = slug(command)
    candidates = [primary]

    # For 'show ip route', accept both CIDR and prefix+netmask slug formats
    match = re.match(
        r"^show ip route\s+([0-9\.\/]+)(?:\s+([0-9\.]+))?$",
        command.strip(),
        re.IGNORECASE,
    )
    if match:
        arg1, arg2 = match.group(1), match.group(2)
        try:
            if arg2:
                net = ipaddress.IPv4Network(f"{arg1}/{arg2}", strict=False)
                alt = slug(f"show ip route {net.network_address}/{net.prefixlen}")
                if alt not in candidates:
                    candidates.append(alt)
            elif "/" in arg1:
                net = ipaddress.IPv4Network(arg1, strict=False)
                alt = slug(f"show ip route {net.network_address} {net.netmask}")
                if alt not in candidates:
                    candidates.append(alt)
        except ValueError:
            pass

    # For 'show route-map <name>', also accept 'show route-map'
    if command.strip().lower().startswith("show route-map "):
        alt = slug("show route-map")
        if alt not in candidates:
            candidates.append(alt)

    return candidates


class MockDevice:
    """Mock network device backed by frozen filesystem fixtures."""

    def __init__(
        self,
        name: str,
        fixtures_root: Path = Path("tests/fixtures"),
        scenario: str = "baseline",
    ) -> None:
        self.name = name
        self.fixtures_root = fixtures_root
        self.scenario = scenario
        self.pushed_configs: list[list[str]] = []
        self.command_history: list[str] = []

    def set_scenario(self, scenario: str) -> None:
        """Switch active scenario (e.g., 'baseline' -> 'faulted/T3')."""
        self.scenario = scenario

    def send_show(self, command: str) -> str:
        """Read frozen output from fixture file corresponding to command."""
        self.command_history.append(command)
        candidates = _candidate_slugs(command)

        # 1. Check primary fixtures_root for active scenario
        for s in candidates:
            fp = self.fixtures_root / self.scenario / self.name / f"{s}.txt"
            if fp.exists():
                return fp.read_text(encoding="utf-8")

        # 2. Check baseline in primary fixtures_root if active scenario is faulted
        if self.scenario != "baseline":
            for s in candidates:
                fp = self.fixtures_root / "baseline" / self.name / f"{s}.txt"
                if fp.exists():
                    return fp.read_text(encoding="utf-8")

        # 3. Only fall back to synthetic demo fixtures if using default tests/fixtures root
        if self.fixtures_root == Path("tests/fixtures"):
            synthetic_root = Path("tests/synthetic/fixtures")
            # Active scenario in synthetic
            for s in candidates:
                sp = synthetic_root / self.scenario / self.name / f"{s}.txt"
                if sp.exists():
                    return sp.read_text(encoding="utf-8")

            # Baseline scenario in synthetic
            if self.scenario != "baseline":
                for s in candidates:
                    sp = synthetic_root / "baseline" / self.name / f"{s}.txt"
                    if sp.exists():
                        return sp.read_text(encoding="utf-8")

        expected_path = self.fixtures_root / self.scenario / self.name / f"{candidates[0]}.txt"
        raise FixtureMissing(
            f"Fixture missing: capture '{command}' on {self.name} (expected at {expected_path})"
        )

    def push_config(self, commands: list[str]) -> str:
        """Record configuration commands without modifying live hardware."""
        self.pushed_configs.append(commands)
        return ""

    def close(self) -> None:
        """No-op cleanup for mock device."""
        pass
