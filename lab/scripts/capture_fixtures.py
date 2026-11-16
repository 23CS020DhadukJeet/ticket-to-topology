"""Script to capture baseline fixture outputs from the live lab using Netmiko."""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import yaml  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from netmiko import ConnectHandler  # noqa: E402

from t2t.devices.slug import slug  # noqa: E402

PHASE_1_COMMANDS = [
    "show version",
    "show ip route",
    "show ip route 10.10.1.0 255.255.255.0",
    "show ip route 10.10.2.0 255.255.255.0",
    "show ip route 10.10.99.0 255.255.255.0",
    "show ip route 172.16.10.0 255.255.255.0",
    "show ip route 172.16.20.16 255.255.255.240",
    "show ip protocols",
    "show ip eigrp neighbors",
    "show ip ospf neighbor",
    "show route-map",
    "show running-config | section router|route-map|prefix-list",
]


def load_inventory(inventory_path: Path) -> dict:
    """Load and parse inventory YAML file."""
    if not inventory_path.exists():
        raise FileNotFoundError(
            f"Inventory file not found at {inventory_path}. "
            "Please copy lab/inventory.example.yaml to lab/inventory.yaml and configure it."
        )
    with inventory_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid inventory format in {inventory_path}")
        return data


def capture_router(
    router: dict,
    defaults: dict,
    username: str,
    password: str,
    output_dir: Path,
) -> None:
    """Connect to a router, execute capture commands, and save raw text outputs."""
    router_name = router["name"]
    host = router["host"]
    device_type = router.get("device_type") or defaults.get("device_type", "cisco_xe")

    router_dir = output_dir / router_name
    router_dir.mkdir(parents=True, exist_ok=True)

    print(f"Connecting to {router_name} ({host})...")
    conn_params = {
        "device_type": device_type,
        "host": host,
        "username": username,
        "password": password,
        "conn_timeout": 15,
        "auth_timeout": 15,
        "banner_timeout": 15,
    }

    with ConnectHandler(**conn_params) as net_connect:
        for cmd in PHASE_1_COMMANDS:
            print(f"  [{router_name}] Running: {cmd}")
            raw_output = net_connect.send_command(cmd, read_timeout=30.0)
            cmd_slug = slug(cmd)
            slug_path = router_dir / f"{cmd_slug}.txt"
            slug_path.write_text(raw_output, encoding="utf-8")
            print(f"    -> Saved to {slug_path}")


def main() -> None:
    """Run capture against all routers in inventory."""
    if "--mock" in sys.argv:
        print(
            "Mock mode requested: generating synthetic demo fixtures without a virtual machine..."
        )
        from lab.scripts.generate_synthetic_fixtures import (
            generate_baseline_fixtures,
            generate_faulted_fixtures,
        )

        generate_baseline_fixtures()
        generate_faulted_fixtures()
        print("Done! You can now use all commands offline with --replay.")
        return

    load_dotenv()
    username = os.getenv("LAB_USERNAME", "admin")
    password = os.getenv("LAB_PASSWORD", "")

    if not password:
        print("Error: LAB_PASSWORD must be set in .env to capture fixtures.", file=sys.stderr)
        print(
            "Tip: If running without a virtual machine, "
            "run 'python lab/scripts/capture_fixtures.py --mock'."
        )
        sys.exit(1)

    inv_path = Path("lab/inventory.yaml")
    if not inv_path.exists():
        inv_path = Path("lab/inventory.example.yaml")

    try:
        inventory = load_inventory(inv_path)
    except Exception as err:
        print(f"Error loading inventory: {err}", file=sys.stderr)
        sys.exit(1)

    defaults = inventory.get("defaults", {})
    routers = inventory.get("routers", [])
    output_base = Path("tests/fixtures/baseline")
    captured_count = 0

    for router in routers:
        try:
            capture_router(
                router=router,
                defaults=defaults,
                username=username,
                password=password,
                output_dir=output_base,
            )
            captured_count += 1
        except Exception as err:
            print(f"Failed capturing {router.get('name')}: {err}", file=sys.stderr)

    if captured_count == 0:
        print(
            "\nNote: All router connections failed. If you do not have a virtual machine running,\n"
            "run 'python lab/scripts/capture_fixtures.py --mock' to generate demo fixtures"
            " for --replay mode.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
