"""Audit service coordinating configuration collection and risk evaluation."""

from pathlib import Path

from t2t.audit.model import DeviceModel, parse_device_model
from t2t.audit.report import AuditReport
from t2t.audit.rules import run_audit
from t2t.config import Inventory, Settings
from t2t.devices.session import DeviceSession
from t2t.errors import T2TError

AUDIT_SECTION_COMMAND = "show running-config | section router|route-map|prefix-list|access-list"


class AuditService:
    """Service governing configuration gathering (read-only or offline) and audit execution."""

    def __init__(
        self,
        inventory: Inventory | None = None,
        settings: Settings | None = None,
        replay: bool = False,
        strict_host_keys: bool = False,
    ) -> None:
        self.inventory = inventory
        self.settings = settings
        self.replay = replay
        self.strict_host_keys = strict_host_keys

    def load_from_directory(self, dir_path: Path) -> list[DeviceModel]:
        """Load and parse saved configuration files from an offline directory.

        Performs strictly zero network or socket operations.
        """
        if not dir_path.exists() or not dir_path.is_dir():
            raise FileNotFoundError(f"Configuration directory not found: {dir_path}")

        models: list[DeviceModel] = []

        # Case 1: Check for flat .cfg / .txt files (e.g. R1.cfg, R2.cfg)
        cfg_files = sorted(dir_path.glob("*.cfg"))
        if not cfg_files:
            cfg_files = sorted(dir_path.glob("*.txt"))

        if cfg_files:
            for f in cfg_files:
                text = f.read_text(encoding="utf-8")
                models.append(parse_device_model(f.stem, text))
            return models

        # Case 2: Check for per-router subdirectories (e.g. R1/, R2/)
        for sub in sorted(dir_path.iterdir()):
            if sub.is_dir():
                # Prefer section command or running-config
                target_file = None
                for fname in [
                    "show_running_config_section_router_route_map_prefix_list.txt",
                    "show_running_config.txt",
                    f"{sub.name}.cfg",
                    f"{sub.name}.txt",
                ]:
                    candidate = sub / fname
                    if candidate.exists():
                        target_file = candidate
                        break

                if target_file is None:
                    # Fallback: take first .txt or .cfg in folder
                    fallback = next(
                        (f for f in sub.iterdir() if f.suffix in (".txt", ".cfg")),
                        None,
                    )
                    target_file = fallback

                if target_file and target_file.exists():
                    text = target_file.read_text(encoding="utf-8")
                    models.append(parse_device_model(sub.name, text))

        if not models:
            raise ValueError(f"No router configuration files found in {dir_path}")

        return models

    def collect_from_network(self) -> list[DeviceModel]:
        """Collect running configurations across all lab routers in read_only mode."""
        if not self.inventory or not self.settings:
            raise T2TError("Inventory and settings are required for network audit.")

        models: list[DeviceModel] = []
        with DeviceSession(
            inventory=self.inventory,
            settings=self.settings,
            read_only=True,
            replay=self.replay,
        ) as session:
            for router in sorted(self.inventory.routers, key=lambda r: r.name):
                router_name = router.name
                try:
                    output = session.show(router_name, AUDIT_SECTION_COMMAND)
                except Exception:
                    output = session.show(router_name, "show running-config")

                models.append(parse_device_model(router_name, output))

        return models

    def execute_audit(
        self,
        from_dir: Path | None = None,
        fail_on: str = "medium",
    ) -> AuditReport:
        """Execute audit against offline directory or live network devices."""
        models = self.load_from_directory(from_dir) if from_dir else self.collect_from_network()
        findings = run_audit(models)

        device_list = [m.name for m in models]
        config_hashes = {m.name: m.config_sha256 for m in models}

        return AuditReport(
            device_list=device_list,
            config_hashes=config_hashes,
            findings=findings,
            fail_on=fail_on,
        )
