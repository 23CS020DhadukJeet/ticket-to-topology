"""Unit tests for fault loader schema and catalog validation (U4.1)."""

from pathlib import Path

import pytest

from t2t.config import Inventory, Router
from t2t.errors import FaultInvalid


@pytest.fixture
def test_inventory() -> Inventory:
    """Fixture providing a standard test inventory."""
    return Inventory(
        defaults={"device_type": "cisco_xe"},
        routers=[
            Router(name="R1", host="192.168.100.11", role="branch"),
            Router(name="R2", host="192.168.100.12", role="asbr"),
            Router(name="R3", host="192.168.100.13", role="asbr"),
            Router(name="R4", host="192.168.100.14", role="hq"),
        ],
    )


def test_u4_1_loader_rejects_missing_revert(tmp_path: Path, test_inventory: Inventory) -> None:
    """U4.1: Fault with router in inject missing from revert is rejected."""
    from t2t.faults.loader import load_fault

    fault_yaml = """
id: T100
title: Missing revert router
level: 2
symptom_class: redundancy
objectives: [redistribution]
inject:
  R2: ["router ospf 1", "no distance ospf external 171"]
revert:
  R3: ["router ospf 1", "distance ospf external 171"]
flows:
  - {src: 172.16.10.10, dst: 10.10.99.1, note: HQ to vendor}
business_context: Test business context description.
root_cause: Test root cause explanation.
key_concepts: [administrative distance]
checks:
  - id: c1
    kind: route_present
    router: R2
    prefix: 10.10.99.0/24
    params: {protocol: eigrp}
hints:
  1: Hint 1
  2: Hint 2
  3: Hint 3
"""
    f_path = tmp_path / "bad_revert.yaml"
    f_path.write_text(fault_yaml, encoding="utf-8")

    with pytest.raises(FaultInvalid, match="revert"):
        load_fault(f_path, test_inventory)


def test_u4_1_loader_rejects_unknown_router(tmp_path: Path, test_inventory: Inventory) -> None:
    """U4.1: Fault targeting an unknown router not in inventory is rejected."""
    from t2t.faults.loader import load_fault

    fault_yaml = """
id: T101
title: Unknown router fault
level: 2
symptom_class: redundancy
objectives: [redistribution]
inject:
  R99: ["interface GigabitEthernet1", "shutdown"]
revert:
  R99: ["interface GigabitEthernet1", "no shutdown"]
flows:
  - {src: 172.16.10.10, dst: 10.10.99.1, note: HQ to vendor}
business_context: Test business context description.
root_cause: Test root cause explanation.
key_concepts: [shutdown]
checks:
  - id: c1
    kind: route_present
    router: R1
    prefix: 10.10.99.0/24
    params: {protocol: eigrp}
hints:
  1: Hint 1
  2: Hint 2
  3: Hint 3
"""
    f_path = tmp_path / "unknown_router.yaml"
    f_path.write_text(fault_yaml, encoding="utf-8")

    with pytest.raises(FaultInvalid, match="unknown router|R99"):
        load_fault(f_path, test_inventory)


def test_u4_1_loader_rejects_duplicate_id(tmp_path: Path, test_inventory: Inventory) -> None:
    """U4.1: Catalog with duplicate fault IDs is rejected."""
    from t2t.faults.loader import load_catalog

    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()

    fault_base = """
id: T1
title: Fault {num}
level: 2
symptom_class: redundancy
objectives: [redistribution]
inject:
  R2: ["router ospf 1"]
revert:
  R2: ["router ospf 1"]
flows:
  - {src: 172.16.10.10, dst: 10.10.99.1, note: HQ to vendor}
business_context: Test business context description.
root_cause: Test root cause explanation.
key_concepts: [ospf]
checks:
  - id: c1
    kind: route_present
    router: R2
    prefix: 10.10.99.0/24
    params: {protocol: eigrp}
hints:
  1: Hint 1
  2: Hint 2
  3: Hint 3
"""
    (catalog_dir / "f1.yaml").write_text(fault_base.replace("{num}", "1"), encoding="utf-8")
    (catalog_dir / "f2.yaml").write_text(fault_base.replace("{num}", "2"), encoding="utf-8")

    with pytest.raises(FaultInvalid, match="duplicate.*id|T1"):
        load_catalog(catalog_dir, test_inventory)


def test_u4_1_loader_rejects_zero_checks(tmp_path: Path, test_inventory: Inventory) -> None:
    """U4.1: Fault with zero checks is rejected."""
    from t2t.faults.loader import load_fault

    fault_yaml = """
id: T102
title: Zero checks fault
level: 2
symptom_class: redundancy
objectives: [redistribution]
inject:
  R2: ["router ospf 1"]
revert:
  R2: ["router ospf 1"]
flows:
  - {src: 172.16.10.10, dst: 10.10.99.1, note: HQ to vendor}
business_context: Test business context description.
root_cause: Test root cause explanation.
key_concepts: [ospf]
checks: []
hints:
  1: Hint 1
  2: Hint 2
  3: Hint 3
"""
    f_path = tmp_path / "zero_checks.yaml"
    f_path.write_text(fault_yaml, encoding="utf-8")

    with pytest.raises(FaultInvalid, match="check"):
        load_fault(f_path, test_inventory)


def test_u4_1_loader_rejects_wrong_hint_count(tmp_path: Path, test_inventory: Inventory) -> None:
    """U4.1: Fault with wrong hint count (not exactly 3) is rejected."""
    from t2t.faults.loader import load_fault

    fault_yaml = """
id: T103
title: Wrong hints fault
level: 2
symptom_class: redundancy
objectives: [redistribution]
inject:
  R2: ["router ospf 1"]
revert:
  R2: ["router ospf 1"]
flows:
  - {src: 172.16.10.10, dst: 10.10.99.1, note: HQ to vendor}
business_context: Test business context description.
root_cause: Test root cause explanation.
key_concepts: [ospf]
checks:
  - id: c1
    kind: route_present
    router: R2
    prefix: 10.10.99.0/24
    params: {protocol: eigrp}
hints:
  1: Hint 1
  2: Hint 2
"""
    f_path = tmp_path / "wrong_hints.yaml"
    f_path.write_text(fault_yaml, encoding="utf-8")

    with pytest.raises(FaultInvalid, match="hint"):
        load_fault(f_path, test_inventory)


def test_loader_file_and_directory_errors(tmp_path: Path, test_inventory: Inventory) -> None:
    """Loader raises FaultInvalid on missing files or directories."""
    from t2t.faults.loader import load_baseline_checks, load_catalog, load_fault

    with pytest.raises(FaultInvalid, match="not found"):
        load_fault(tmp_path / "nonexistent.yaml", test_inventory)

    with pytest.raises(FaultInvalid, match="not found"):
        load_catalog(tmp_path / "nonexistent_dir", test_inventory)

    with pytest.raises(FaultInvalid, match="not found"):
        load_baseline_checks(tmp_path / "nonexistent_baseline.yaml")


def test_loader_malformed_yaml(tmp_path: Path, test_inventory: Inventory) -> None:
    """Loader raises FaultInvalid on non-dict YAML or invalid baseline checks."""
    from t2t.faults.loader import load_baseline_checks, load_fault

    f_non_dict = tmp_path / "not_dict.yaml"
    f_non_dict.write_text("- item1\n- item2\n", encoding="utf-8")
    with pytest.raises(FaultInvalid, match="dictionary"):
        load_fault(f_non_dict, test_inventory)

    f_base_bad = tmp_path / "bad_baseline.yaml"
    f_base_bad.write_text("not_checks: 123\n", encoding="utf-8")
    with pytest.raises(FaultInvalid, match="checks.*list"):
        load_baseline_checks(f_base_bad)

    f_base_empty = tmp_path / "empty_baseline.yaml"
    f_base_empty.write_text("checks: []\n", encoding="utf-8")
    with pytest.raises(FaultInvalid, match="non-empty"):
        load_baseline_checks(f_base_empty)
