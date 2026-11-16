"""Mock device implementation for deterministic offline replay and CI testing."""

from pathlib import Path

from t2t.devices.slug import slug
from t2t.errors import FixtureMissing


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
        cmd_slug = slug(command)
        fixture_path = self.fixtures_root / self.scenario / self.name / f"{cmd_slug}.txt"

        if not fixture_path.exists():
            raise FixtureMissing(
                f"Fixture missing: capture '{command}' on {self.name} (expected at {fixture_path})"
            )

        return fixture_path.read_text(encoding="utf-8")

    def push_config(self, commands: list[str]) -> str:
        """Record configuration commands without modifying live hardware."""
        self.pushed_configs.append(commands)
        return ""

    def close(self) -> None:
        """No-op cleanup for mock device."""
        pass
