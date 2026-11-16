"""Unit tests for offline fault regression and baseline guard (U4.5, U3.5)."""

from pathlib import Path

from t2t.config import load_inventory, load_settings
from t2t.devices.session import DeviceSession
from t2t.faults.engine import FaultEngine
from t2t.faults.loader import load_baseline_checks, load_catalog
from t2t.faults.qualify import qualify_fault


def test_u4_5_and_u3_5_baseline_guard() -> None:
    """U3.5 & U4.5: For every fault in the catalog, all its checks pass on baseline."""
    settings = load_settings()
    inventory = load_inventory(settings.t2t_inventory)

    catalog_path = Path("src/t2t/faults/catalog")
    assert catalog_path.exists(), "Fault catalog directory does not exist"

    faults = load_catalog(catalog_path, inventory)
    assert len(faults) >= 10, f"Expected 10 faults from Appendix A, found {len(faults)}"

    # Verify each fault has required fields per Appendix A
    for fault_id, fault in faults.items():
        assert len(fault.checks) >= 1, f"Fault {fault_id} must have >= 1 check"
        assert len(fault.hints) == 3, f"Fault {fault_id} must have exactly 3 hints"
        assert fault.symptom_class in ["outage", "redundancy", "suboptimal", "latent"]
        assert len(fault.objectives) >= 1
        assert len(fault.root_cause) >= 10
        assert len(fault.key_concepts) >= 1


def test_u4_6_offline_qualification_with_synthetic_fixtures(tmp_path: Path) -> None:
    """Verify qualify_fault runs deterministically offline in replay mode."""
    settings = load_settings()
    inventory = load_inventory(settings.t2t_inventory)
    catalog = load_catalog(Path("src/t2t/faults/catalog"), inventory)
    baseline_checks = load_baseline_checks(Path("src/t2t/faults/baseline.yaml"))

    with DeviceSession(inventory=inventory, settings=settings, replay=True) as session:
        engine = FaultEngine(
            session=session,
            state_file=tmp_path / "state.json",
            baseline_checks=baseline_checks,
        )
        report = qualify_fault(
            fault=catalog["T3"],
            engine=engine,
            baseline_checks=baseline_checks,
            runs=1,
            report_dir=tmp_path / "evidence",
        )
        assert report.qualified
        assert len(report.runs) == 1
        assert report.runs[0].success
        assert len(report.runs[0].inject_failed_checks) > 0
