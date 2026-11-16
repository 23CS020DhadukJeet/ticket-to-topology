"""Integration tests for fault qualification, reset cycles, and recovery on live lab (I4.1–I4.4).

Run only with live routers: pytest -m lab
"""

from pathlib import Path

import pytest

from t2t.config import load_inventory, load_settings
from t2t.devices.session import DeviceSession
from t2t.faults.engine import FaultEngine
from t2t.faults.loader import load_baseline_checks, load_catalog
from t2t.faults.qualify import qualify_all
from t2t.faults.state import clear_active_fault, get_state


@pytest.mark.lab
def test_i4_1_qualify_all_three_runs() -> None:
    """I4.1: Qualify all faults in the catalog 3 times consecutively on live lab."""
    settings = load_settings()
    inventory = load_inventory(settings.t2t_inventory)
    catalog = load_catalog(Path("src/t2t/faults/catalog"), inventory)
    baseline_checks = load_baseline_checks(Path("src/t2t/faults/baseline.yaml"))

    with DeviceSession(inventory=inventory, settings=settings, read_only=False) as session:
        engine = FaultEngine(session=session, inventory=inventory, baseline_checks=baseline_checks)
        reports = qualify_all(
            catalog=catalog,
            engine=engine,
            baseline_checks=baseline_checks,
            runs=3,
            capture=True,
        )
        for rep in reports:
            assert rep.qualified, f"Fault {rep.fault_id} failed qualification"


@pytest.mark.lab
def test_i4_2_twenty_reset_cycles() -> None:
    """I4.2: 20 consecutive reset+baseline cycles with zero failures (Objective O2)."""
    settings = load_settings()
    inventory = load_inventory(settings.t2t_inventory)
    baseline_checks = load_baseline_checks(Path("src/t2t/faults/baseline.yaml"))

    with DeviceSession(inventory=inventory, settings=settings, read_only=False) as session:
        engine = FaultEngine(session=session, inventory=inventory, baseline_checks=baseline_checks)
        for i in range(1, 21):
            statuses = engine.reset_lab(baseline_checks=baseline_checks)
            for r_name, stat in statuses.items():
                assert stat.success, f"Cycle {i}: Reset failed on {r_name}: {stat.output}"


@pytest.mark.lab
def test_i4_3_reset_force_recovers_interrupted_session() -> None:
    """I4.3: Simulate mid-session interruption and recover with reset --force."""
    settings = load_settings()
    inventory = load_inventory(settings.t2t_inventory)
    baseline_checks = load_baseline_checks(Path("src/t2t/faults/baseline.yaml"))

    # Force clear and reset lab
    clear_active_fault(force=True)
    with DeviceSession(inventory=inventory, settings=settings, read_only=False) as session:
        engine = FaultEngine(session=session, inventory=inventory, baseline_checks=baseline_checks)
        statuses = engine.reset_lab(baseline_checks=baseline_checks)
        assert all(s.success for s in statuses.values())
        assert get_state().active_fault is None


@pytest.mark.lab
def test_i4_4_revert_leaves_no_diff() -> None:
    """I4.4: Verify configuration after revert has no drift in touched sections."""
    settings = load_settings()
    inventory = load_inventory(settings.t2t_inventory)
    catalog = load_catalog(Path("src/t2t/faults/catalog"), inventory)
    baseline_checks = load_baseline_checks(Path("src/t2t/faults/baseline.yaml"))

    fault = catalog["T3"]
    with DeviceSession(inventory=inventory, settings=settings, read_only=False) as session:
        engine = FaultEngine(session=session, inventory=inventory, baseline_checks=baseline_checks)
        engine.reset_lab(baseline_checks=baseline_checks)
        engine.inject(fault)
        engine.revert(fault)

        # Check touched section on R3
        out = session.show("R3", "show running-config | section router ospf")
        assert "distance ospf external 171" in out
