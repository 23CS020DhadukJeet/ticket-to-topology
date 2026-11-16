"""Fault definition loader and YAML schema validation.

NOTE: Per AGENTS.md Hard Rule 3, t2t.faults must never import t2t.ai.
"""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError

from t2t.config import Inventory
from t2t.errors import FaultInvalid
from t2t.models import Check
from t2t.verify.engine import validate_check


class FlowModel(BaseModel):
    """Network flow model for business traffic checks."""

    src: str = Field(min_length=1)
    dst: str = Field(min_length=1)
    note: str = Field(min_length=1)


class FaultModel(BaseModel):
    """Validated fault configuration loaded from catalog."""

    id: str = Field(pattern=r"^T\d+$")
    title: str = Field(min_length=3)
    level: int = Field(ge=1, le=5)
    symptom_class: Literal["outage", "redundancy", "suboptimal", "latent"]
    objectives: list[str] = Field(min_length=1)
    inject: dict[str, list[str]] = Field(min_length=1)
    revert: dict[str, list[str]] = Field(min_length=1)
    flows: list[FlowModel] = Field(min_length=1)
    business_context: str = Field(min_length=5)
    root_cause: str = Field(min_length=5)
    key_concepts: list[str] = Field(min_length=1)
    checks: list[Check] = Field(min_length=1)
    hints: dict[int, str]
    observed_symptom: str = ""


def load_fault(path: Path, inventory: Inventory) -> FaultModel:
    """Load and validate a single fault YAML file.

    Raises:
        FaultInvalid: If YAML syntax is invalid, schema validation fails,
                      router names are unknown, or revert counterparts are missing.
    """
    if not path.is_file():
        raise FaultInvalid(f"Fault file not found: {path}")

    try:
        content = path.read_text(encoding="utf-8")
        data: Any = yaml.safe_load(content)
    except Exception as err:
        raise FaultInvalid(f"Failed to parse YAML in {path.name}: {err}") from err

    if not isinstance(data, dict):
        raise FaultInvalid(f"Expected dictionary in {path.name}, got {type(data).__name__}")

    # Validate schema via Pydantic
    try:
        fault = FaultModel.model_validate(data)
    except ValidationError as err:
        raise FaultInvalid(f"Fault schema validation error in {path.name}: {err}") from err

    # Hint count validation: exactly 3 hints (keys 1, 2, 3)
    if set(fault.hints.keys()) != {1, 2, 3}:
        raise FaultInvalid(
            f"Fault {fault.id} in {path.name} must have exactly 3 hints with keys 1, 2, 3."
        )

    # Check inventory router membership
    known_routers = {r.name for r in inventory.routers}
    for r in fault.inject:
        if r not in known_routers:
            raise FaultInvalid(f"Fault {fault.id} targets unknown router '{r}' not in inventory.")
    for r in fault.revert:
        if r not in known_routers:
            raise FaultInvalid(f"Fault {fault.id} references unknown router '{r}' in revert.")

    # Check counterpart rule: every router in inject must have a counterpart in revert
    inject_routers = set(fault.inject.keys())
    revert_routers = set(fault.revert.keys())
    if inject_routers != revert_routers:
        missing_in_revert = inject_routers - revert_routers
        missing_in_inject = revert_routers - inject_routers
        diff_msg = []
        if missing_in_revert:
            diff_msg.append(f"missing in revert: {missing_in_revert}")
        if missing_in_inject:
            diff_msg.append(f"missing in inject: {missing_in_inject}")
        raise FaultInvalid(
            f"Fault {fault.id} router mismatch between inject and revert: {', '.join(diff_msg)}."
        )

    # Validate each check in checks against verify schema
    for c in fault.checks:
        validate_check(c)

    return fault


def load_catalog(catalog_dir: Path, inventory: Inventory) -> dict[str, FaultModel]:
    """Load all fault definitions in catalog directory.

    Raises:
        FaultInvalid: If duplicate IDs exist or any fault is invalid.
    """
    if not catalog_dir.is_dir():
        raise FaultInvalid(f"Catalog directory not found: {catalog_dir}")

    faults: dict[str, FaultModel] = {}
    yaml_files = sorted(list(catalog_dir.glob("*.yaml")) + list(catalog_dir.glob("*.yml")))

    for f_path in yaml_files:
        fault = load_fault(f_path, inventory)
        if fault.id in faults:
            raise FaultInvalid(
                f"Duplicate fault ID '{fault.id}' found in {f_path.name} and another file."
            )
        faults[fault.id] = fault

    return faults


def load_baseline_checks(path: Path) -> list[Check]:
    """Load oracle baseline checks from YAML file.

    Raises:
        FaultInvalid: If file is missing, malformed, or checks are invalid.
    """
    if not path.is_file():
        raise FaultInvalid(f"Baseline file not found: {path}")

    try:
        content = path.read_text(encoding="utf-8")
        data: Any = yaml.safe_load(content)
    except Exception as err:
        raise FaultInvalid(f"Failed to parse baseline YAML in {path.name}: {err}") from err

    if not isinstance(data, dict) or "checks" not in data:
        raise FaultInvalid(f"Baseline file {path.name} must contain a 'checks' list.")

    raw_checks = data["checks"]
    if not isinstance(raw_checks, list) or not raw_checks:
        raise FaultInvalid(f"Baseline checks list in {path.name} must be non-empty.")

    checks: list[Check] = []
    for item in raw_checks:
        try:
            check = Check.model_validate(item)
            validate_check(check)
            checks.append(check)
        except Exception as err:
            raise FaultInvalid(f"Invalid baseline check in {path.name}: {err}") from err

    return checks
