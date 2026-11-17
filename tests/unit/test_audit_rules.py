"""Unit tests for Phase 7 audit rules and fault matrix (U7.1, U7.2, U7.3)."""

from pathlib import Path

from t2t.audit.model import parse_device_model
from t2t.audit.rules import (
    rule_a1,
    rule_a2,
    rule_a3,
    rule_a4,
    rule_a5,
    rule_a6,
    rule_a7,
    run_audit,
)


def _load_devices_from_dir(dir_path: Path) -> list:
    devices = []
    for cfg in sorted(dir_path.glob("*.cfg")):
        devices.append(parse_device_model(cfg.stem, cfg.read_text(encoding="utf-8")))
    return devices


# U7.1: Each rule positive + negative fixture
def test_u7_1_rule_a1_redistribute_without_route_map() -> None:
    pos_dir = Path("tests/synthetic/audit/a1_no_routemap/positive")
    neg_dir = Path("tests/synthetic/audit/a1_no_routemap/negative")

    pos_devs = _load_devices_from_dir(pos_dir)
    neg_devs = _load_devices_from_dir(neg_dir)

    findings_pos = rule_a1(pos_devs)
    assert len(findings_pos) >= 1
    assert any(f.rule_id == "A1" and f.severity == "High" for f in findings_pos)

    findings_neg = rule_a1(neg_devs)
    assert len(findings_neg) == 0


def test_u7_1_rule_a2_eigrp_no_metric() -> None:
    pos_dir = Path("tests/synthetic/audit/a2_eigrp_no_metric/positive")
    neg_dir = Path("tests/synthetic/audit/a2_eigrp_no_metric/negative")

    pos_devs = _load_devices_from_dir(pos_dir)
    neg_devs = _load_devices_from_dir(neg_dir)

    findings_pos = rule_a2(pos_devs)
    assert len(findings_pos) == 1
    assert findings_pos[0].rule_id == "A2"
    assert findings_pos[0].severity == "High"

    findings_neg = rule_a2(neg_devs)
    assert len(findings_neg) == 0


def test_u7_1_rule_a3_ospf_no_subnets() -> None:
    pos_dir = Path("tests/synthetic/audit/a3_ospf_no_subnets/positive")
    neg_dir = Path("tests/synthetic/audit/a3_ospf_no_subnets/negative")

    pos_devs = _load_devices_from_dir(pos_dir)
    neg_devs = _load_devices_from_dir(neg_dir)

    findings_pos = rule_a3(pos_devs)
    assert len(findings_pos) == 1
    assert findings_pos[0].rule_id == "A3"
    assert findings_pos[0].severity == "Medium"

    findings_neg = rule_a3(neg_devs)
    assert len(findings_neg) == 0


def test_u7_1_rule_a4_tag_loop_guard() -> None:
    pos_dir = Path("tests/synthetic/audit/a4_no_tag_loop_guard/positive")
    baseline_dir = Path("tests/synthetic/audit/baseline")

    pos_devs = _load_devices_from_dir(pos_dir)
    base_devs = _load_devices_from_dir(baseline_dir)

    findings_pos = rule_a4(pos_devs)
    assert len(findings_pos) >= 1
    assert any(f.rule_id == "A4" and f.severity == "High" for f in findings_pos)

    findings_base = rule_a4(base_devs)
    assert len(findings_base) == 0


def test_u7_1_rule_a5_ospf_external_distance() -> None:
    pos_dir = Path("tests/synthetic/audit/a5_ospf_distance/positive")
    baseline_dir = Path("tests/synthetic/audit/baseline")

    pos_devs = _load_devices_from_dir(pos_dir)
    base_devs = _load_devices_from_dir(baseline_dir)

    findings_pos = rule_a5(pos_devs)
    assert len(findings_pos) >= 1
    assert any(f.rule_id == "A5" and f.severity == "Medium" for f in findings_pos)

    findings_base = rule_a5(base_devs)
    assert len(findings_base) == 0


def test_u7_1_rule_a6_route_map_permit_and_references() -> None:
    pos_deny = _load_devices_from_dir(
        Path("tests/synthetic/audit/a6_routemap_permit_missing/positive_deny_only")
    )
    pos_missing_pl = _load_devices_from_dir(
        Path("tests/synthetic/audit/a6_routemap_permit_missing/positive_missing_pl")
    )
    base_devs = _load_devices_from_dir(Path("tests/synthetic/audit/baseline"))

    f_deny = rule_a6(pos_deny)
    assert len(f_deny) >= 1
    assert any(f.rule_id == "A6" for f in f_deny)

    f_missing = rule_a6(pos_missing_pl)
    assert len(f_missing) >= 1
    assert any(f.rule_id == "A6" for f in f_missing)

    f_base = rule_a6(base_devs)
    assert len(f_base) == 0


def test_u7_1_rule_a7_metric_type() -> None:
    pos_dir = Path("tests/synthetic/audit/a7_metric_type/positive")
    base_dir = Path("tests/synthetic/audit/baseline")

    pos_devs = _load_devices_from_dir(pos_dir)
    base_devs = _load_devices_from_dir(base_dir)

    findings_pos = rule_a7(pos_devs)
    assert len(findings_pos) >= 1
    assert any(f.rule_id == "A7" for f in findings_pos)

    findings_base = rule_a7(base_devs)
    assert len(findings_base) == 0


# U7.2: Healthy baseline -> 0 findings across all rules
def test_u7_2_healthy_baseline_zero_findings() -> None:
    base_dir = Path("tests/synthetic/audit/baseline")
    devices = _load_devices_from_dir(base_dir)
    assert len(devices) == 4

    findings = run_audit(devices)
    assert len(findings) == 0


# U7.3: Matrix over faulted configs: T1->A4+A5, T2->A2, T3->A5, T4->A3, T6->A6, A1 synthetic
def test_u7_3_fault_matrix_detection() -> None:
    baseline_dir = Path("tests/synthetic/audit/baseline")
    base_devs = {d.name: d.raw_config for d in _load_devices_from_dir(baseline_dir)}

    # T1: Route tag loop guard missing + distance reset
    # In T1: R2 & R3 lack tag deny clauses and default OSPF distance
    t1_r2 = (
        base_devs["R2"]
        .replace("route-map EIGRP-TO-OSPF deny 10\n match tag 200\n!\n", "")
        .replace("distance ospf external 171\n", "")
    )
    t1_r3 = (
        base_devs["R3"]
        .replace("route-map EIGRP-TO-OSPF deny 10\n match tag 200\n!\n", "")
        .replace("distance ospf external 171\n", "")
    )
    devs_t1 = [
        parse_device_model("R1", base_devs["R1"]),
        parse_device_model("R2", t1_r2),
        parse_device_model("R3", t1_r3),
        parse_device_model("R4", base_devs["R4"]),
    ]
    f_t1 = {f.rule_id for f in run_audit(devs_t1)}
    assert "A4" in f_t1
    assert "A5" in f_t1

    # T2: EIGRP missing metric on R2
    t2_r2 = base_devs["R2"].replace("metric 10000 100 255 1 1500 ", "")
    devs_t2 = [
        parse_device_model("R1", base_devs["R1"]),
        parse_device_model("R2", t2_r2),
        parse_device_model("R3", base_devs["R3"]),
        parse_device_model("R4", base_devs["R4"]),
    ]
    f_t2 = {f.rule_id for f in run_audit(devs_t2)}
    assert "A2" in f_t2

    # T3: R3 distance default (110) while R2 has 171
    t3_r3 = base_devs["R3"].replace("distance ospf external 171\n", "")
    devs_t3 = [
        parse_device_model("R1", base_devs["R1"]),
        parse_device_model("R2", base_devs["R2"]),
        parse_device_model("R3", t3_r3),
        parse_device_model("R4", base_devs["R4"]),
    ]
    f_t3 = {f.rule_id for f in run_audit(devs_t3)}
    assert "A5" in f_t3

    # T4: OSPF missing subnets on R2
    t4_r2 = base_devs["R2"].replace(" subnets ", " ")
    devs_t4 = [
        parse_device_model("R1", base_devs["R1"]),
        parse_device_model("R2", t4_r2),
        parse_device_model("R3", base_devs["R3"]),
        parse_device_model("R4", base_devs["R4"]),
    ]
    f_t4 = {f.rule_id for f in run_audit(devs_t4)}
    assert "A3" in f_t4

    # T6: Route-map deny only on R2
    t6_r2 = base_devs["R2"].replace(
        "route-map OSPF-TO-EIGRP permit 20", "route-map OSPF-TO-EIGRP deny 20"
    )
    devs_t6 = [
        parse_device_model("R1", base_devs["R1"]),
        parse_device_model("R2", t6_r2),
        parse_device_model("R3", base_devs["R3"]),
        parse_device_model("R4", base_devs["R4"]),
    ]
    f_t6 = {f.rule_id for f in run_audit(devs_t6)}
    assert "A6" in f_t6
