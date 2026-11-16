"""Unit tests for fault engine inject, revert, reset, and state file (U4.2, U4.4)."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from t2t.clock import FakeClock
from t2t.config import Inventory, Router
from t2t.errors import StateCorrupt


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


def test_u4_2_mock_device_inject_revert(tmp_path: Path, test_inventory: Inventory) -> None:
    """U4.2: FaultEngine inject switches MockDevice scenario; revert restores baseline."""
    from t2t.faults.engine import FaultEngine
    from t2t.faults.loader import load_fault

    fault_yaml = """
id: T3
title: OSPF external AD override removed on R3
level: 2
symptom_class: suboptimal
objectives: [administrative-distance]
inject:
  R3: ["router ospf 1", "no distance ospf external 171"]
revert:
  R3: ["router ospf 1", "distance ospf external 171"]
flows:
  - {src: 172.16.10.10, dst: 10.10.99.1, note: HQ to vendor}
business_context: Test context description.
root_cause: Test root cause.
key_concepts: [administrative distance]
checks:
  - id: c1
    kind: route_present
    router: R3
    prefix: 10.10.99.0/24
    params: {protocol: eigrp, distance: 170}
hints:
  1: Hint 1
  2: Hint 2
  3: Hint 3
"""
    f_path = tmp_path / "T3.yaml"
    f_path.write_text(fault_yaml, encoding="utf-8")
    fault = load_fault(f_path, test_inventory)

    session = MagicMock()
    mock_dev_r3 = MagicMock()
    mock_dev_r3.scenario = "baseline"
    session.devices = {"R3": mock_dev_r3}
    clock = FakeClock()
    state_file = tmp_path / "state.json"

    engine = FaultEngine(
        session=session,
        clock=clock,
        inventory=test_inventory,
        state_file=state_file,
    )

    # Inject
    engine.inject(fault, skip_baseline_check=True)
    session.push_config.assert_called_once_with(
        "R3", ["router ospf 1", "no distance ospf external 171"], reason="inject T3"
    )
    assert mock_dev_r3.set_scenario.called or mock_dev_r3.scenario == "faulted/T3"

    # Revert
    engine.revert(fault)
    assert session.push_config.call_count == 2
    session.push_config.assert_called_with(
        "R3", ["router ospf 1", "distance ospf external 171"], reason="revert T3"
    )


def test_u4_4_state_file_second_inject_refused(tmp_path: Path, test_inventory: Inventory) -> None:
    """U4.4: Second inject is refused when a fault is already active."""
    from t2t.errors import T2TError
    from t2t.faults.engine import FaultEngine
    from t2t.faults.loader import load_fault

    fault_yaml = """
id: T3
title: Fault active test
level: 2
symptom_class: suboptimal
objectives: [administrative-distance]
inject:
  R3: ["router ospf 1"]
revert:
  R3: ["router ospf 1"]
flows:
  - {src: 172.16.10.10, dst: 10.10.99.1, note: HQ to vendor}
business_context: Test context.
root_cause: Test root cause.
key_concepts: [ospf]
checks:
  - id: c1
    kind: route_present
    router: R3
    prefix: 10.10.99.0/24
    params: {protocol: eigrp}
hints:
  1: Hint 1
  2: Hint 2
  3: Hint 3
"""
    f_path = tmp_path / "T3.yaml"
    f_path.write_text(fault_yaml, encoding="utf-8")
    fault = load_fault(f_path, test_inventory)

    session = MagicMock()
    session.devices = {"R3": MagicMock()}
    clock = FakeClock()
    state_file = tmp_path / "state.json"

    engine = FaultEngine(
        session=session,
        clock=clock,
        inventory=test_inventory,
        state_file=state_file,
    )

    engine.inject(fault, skip_baseline_check=True)

    # Second inject should fail
    with pytest.raises((StateCorrupt, T2TError), match="active.*fault|another fault"):
        engine.inject(fault, skip_baseline_check=True)


def test_u4_4_reset_force_clears_stale_state(tmp_path: Path, test_inventory: Inventory) -> None:
    """U4.4: reset --force clears stale state and lock files."""
    from t2t.faults.state import clear_active_fault, get_state

    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps({"active_fault": "T3", "injected_at": "2026-11-17T00:00:00Z", "schema": 1}),
        encoding="utf-8",
    )

    # Clear active fault with force
    clear_active_fault(state_file=state_file, force=True)
    state = get_state(state_file=state_file)
    assert state.active_fault is None


def test_u4_4_corrupt_state_raises_state_corrupt(tmp_path: Path) -> None:
    """U4.4: Malformed state file raises StateCorrupt."""
    from t2t.faults.state import get_state

    state_file = tmp_path / "corrupt_state.json"
    state_file.write_text("{bad json syntax", encoding="utf-8")

    with pytest.raises(StateCorrupt):
        get_state(state_file=state_file)


def test_engine_reset_lab_handles_failures(tmp_path: Path, test_inventory: Inventory) -> None:
    """FaultEngine.reset_lab handles and logs router failures gracefully."""
    from t2t.faults.engine import FaultEngine

    session = MagicMock()

    # R1 fails, R2 throws exception, R3 and R4 succeed
    def push_cfg(r: str, cmds: list[str], reason: str = "") -> str:
        if r == "R1":
            return "% Error: command failed"
        if r == "R2":
            raise RuntimeError("SSH connection lost")
        return "Total configuration of 123 bytes"

    session.push_config.side_effect = push_cfg
    clock = FakeClock()
    state_file = tmp_path / "state.json"

    engine = FaultEngine(
        session=session,
        clock=clock,
        inventory=test_inventory,
        state_file=state_file,
    )

    statuses = engine.reset_lab()
    assert statuses["R1"].success is False
    assert statuses["R2"].success is False
    assert statuses["R3"].success is True
    assert statuses["R4"].success is True


def test_qualify_fault_and_qualify_all(
    tmp_path: Path, test_inventory: Inventory, monkeypatch: Any
) -> None:
    """Qualify fault executes qualification cycles, captures fixtures, and writes reports."""
    from t2t.faults.engine import FaultEngine
    from t2t.faults.loader import load_fault
    from t2t.faults.qualify import qualify_all, qualify_fault
    from t2t.models import CheckResult

    fault_yaml = """
id: T3
title: OSPF AD Override
level: 2
symptom_class: suboptimal
objectives: [administrative-distance]
inject:
  R3: ["router ospf 1"]
revert:
  R3: ["router ospf 1"]
flows:
  - {src: 172.16.10.10, dst: 10.10.99.1, note: HQ to vendor}
business_context: Test business context.
root_cause: Test root cause explanation.
key_concepts: [ospf]
checks:
  - id: c1
    kind: route_present
    router: R3
    prefix: 10.10.99.0/24
    params: {protocol: eigrp}
hints:
  1: Hint 1
  2: Hint 2
  3: Hint 3
"""
    f_path = tmp_path / "T3.yaml"
    f_path.write_text(fault_yaml, encoding="utf-8")
    fault = load_fault(f_path, test_inventory)

    session = MagicMock()
    session.show.return_value = "captured output text"
    session.push_config.return_value = "config applied"
    session.devices = {"R3": MagicMock()}

    clock = FakeClock()
    state_file = tmp_path / "state.json"
    engine = FaultEngine(
        session=session,
        clock=clock,
        inventory=test_inventory,
        state_file=state_file,
    )

    # Mock run_all: simulate pass during baseline/revert, and fail during inject
    step = 0

    def mock_run_all(checks: list[Any], sess: Any, clk: Any) -> tuple[list[CheckResult], bool]:
        nonlocal step
        step += 1
        # step 1: pre-baseline (pass)
        # step 2: pre-fault (pass)
        # step 3: inject (fail)
        # step 4: post-revert (pass)
        # step 5: post-baseline (pass)
        is_inject_check = step % 5 == 3
        if is_inject_check:
            res = CheckResult(
                check_id="c1", passed=False, expected="pass", observed="fail", message="failed"
            )
            return [res], False
        res_pass = CheckResult(
            check_id="c1", passed=True, expected="pass", observed="pass", message="ok"
        )
        return [res_pass], True

    monkeypatch.setattr("t2t.faults.qualify.run_all", mock_run_all)

    evidence_dir = tmp_path / "evidence"
    fixtures_dir = tmp_path / "fixtures"

    report = qualify_fault(
        fault=fault,
        engine=engine,
        baseline_checks=[],
        runs=2,
        capture=True,
        report_dir=evidence_dir,
        fixtures_root=fixtures_dir,
    )

    assert report.qualified is True
    assert len(report.runs) == 2
    assert (evidence_dir / "qualification-T3.json").exists()
    assert (evidence_dir / "qualification-T3.md").exists()

    # Also test qualify_all
    reports = qualify_all(
        catalog={"T3": fault},
        engine=engine,
        baseline_checks=[],
        runs=1,
        capture=False,
        report_dir=evidence_dir,
    )
    assert len(reports) == 1
    assert reports[0].fault_id == "T3"


def test_engine_inject_and_reset_with_baseline(
    tmp_path: Path, test_inventory: Inventory, monkeypatch: Any
) -> None:
    """FaultEngine runs wait_for_baseline when baseline checks are specified."""
    from t2t.faults.engine import FaultEngine
    from t2t.faults.loader import load_fault
    from t2t.models import Check, CheckResult

    fault_yaml = """
id: T3
title: OSPF AD Override
level: 2
symptom_class: suboptimal
objectives: [administrative-distance]
inject:
  R3: ["router ospf 1"]
revert:
  R3: ["router ospf 1"]
flows:
  - {src: 172.16.10.10, dst: 10.10.99.1, note: HQ to vendor}
business_context: Test business context.
root_cause: Test root cause explanation.
key_concepts: [ospf]
checks:
  - id: c1
    kind: route_present
    router: R3
    prefix: 10.10.99.0/24
    params: {protocol: eigrp}
hints:
  1: Hint 1
  2: Hint 2
  3: Hint 3
"""
    f_path = tmp_path / "T3.yaml"
    f_path.write_text(fault_yaml, encoding="utf-8")
    fault = load_fault(f_path, test_inventory)

    session = MagicMock()
    session.show.return_value = "route info"
    session.push_config.return_value = "config OK"
    clock = FakeClock()
    state_file = tmp_path / "state.json"

    base_check = Check(
        id="b1",
        kind="route_present",
        router="R3",
        prefix="10.10.99.0/24",
        params={"protocol": "eigrp"},
    )

    engine = FaultEngine(
        session=session,
        clock=clock,
        inventory=test_inventory,
        state_file=state_file,
        baseline_checks=[base_check],
    )

    monkeypatch.setattr(
        "t2t.faults.engine.wait_for_baseline",
        lambda sess, clk, chks, timeout=60.0: [
            CheckResult(check_id="b1", passed=True, expected="ok", observed="ok", message="ok")
        ],
    )

    # Inject with baseline check
    engine.inject(fault, skip_baseline_check=False)

    # Reset lab with baseline check
    statuses = engine.reset_lab(baseline_checks=[base_check])
    assert all(s.success for s in statuses.values())


def test_state_file_force_timeout_cleanup(tmp_path: Path, monkeypatch: Any) -> None:
    """clear_active_fault with force=True removes lockfile if FileLock times out."""
    from filelock import Timeout

    from t2t.faults.state import clear_active_fault, get_state

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"active_fault": "T1", "injected_at": null, "schema": 1}', encoding="utf-8"
    )

    class MockLock:
        def __enter__(self) -> None:
            raise Timeout("mock lock timeout")

        def __exit__(self, *args: Any) -> None:
            pass

    monkeypatch.setattr("t2t.faults.state._get_lock", lambda sf: MockLock())

    # Force should bypass and clear
    clear_active_fault(state_file=state_file, force=True)
    # Restore real lock to read
    monkeypatch.undo()
    state = get_state(state_file=state_file)
    assert state.active_fault is None
