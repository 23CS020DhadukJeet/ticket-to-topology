"""Unit tests U3.3, U3.4, U3.5, U3.6 for verification engine."""

from unittest.mock import MagicMock

import pytest

from t2t.clock import FakeClock
from t2t.errors import FaultInvalid
from t2t.models import Check
from t2t.verify.engine import run_all, validate_check


def test_u3_6_unknown_kind_or_bad_params_fails_validation() -> None:
    """U3.6: unknown check kind or invalid parameters raises FaultInvalid at load time."""
    # Unknown kind
    with pytest.raises(FaultInvalid, match="Unknown check kind"):
        validate_check(Check(id="c1", kind="non_existent_kind", router="R1"))

    # Missing mandatory params
    with pytest.raises(FaultInvalid, match="Invalid params"):
        validate_check(Check(id="c2", kind="neighbor_up", router="R1", params={}))

    # Invalid ping params
    with pytest.raises(FaultInvalid, match="Invalid params"):
        validate_check(Check(id="c3", kind="ping", router="R1", params={"source": "1.1.1.1"}))


def test_u3_3_route_present_pass_and_fail() -> None:
    """U3.3: route_present passes when attributes match, fails when absent or mismatch."""
    session = MagicMock()
    # 1. Pass case
    session.show.return_value = (
        "Routing entry for 10.10.1.0/24\n"
        '  Known via "eigrp 100", distance 90, metric 1308160, type internal\n'
        "  Route tag 100\n"
        "  Routing Descriptor Blocks:\n"
        "  * 10.1.12.1, from 10.1.12.1, 00:15:32 ago, via GigabitEthernet2\n"
        "    10.1.13.1, from 10.1.13.1, 00:15:32 ago, via GigabitEthernet3\n"
    )

    check_pass = Check(
        id="c1",
        kind="route_present",
        router="R2",
        prefix="10.10.1.0 255.255.255.0",
        params={
            "protocol": "eigrp",
            "distance": 90,
            "tag": 100,
            "min_paths": 2,
            "next_hops_include": ["10.1.12.1", "10.1.13.1"],
        },
    )
    results, verdict = run_all([check_pass], session)
    assert verdict is True
    assert results[0].passed is True

    # 2. Fail cases:
    # Missing from RIB
    session.show.return_value = "% Network not in table\n"
    results, verdict = run_all([check_pass], session)
    assert verdict is False
    assert "missing" in results[0].message

    # Tag mismatch
    session.show.return_value = (
        "Routing entry for 10.10.1.0/24\n"
        '  Known via "eigrp 100", distance 90, metric 1308160\n'
        "  Route tag 200\n"
    )
    check_bad_tag = Check(id="c_tag", kind="route_present", router="R2", params={"tag": 100})
    results, verdict = run_all([check_bad_tag], session)
    assert verdict is False
    assert "tag" in results[0].message

    # Min paths mismatch
    check_min_paths = Check(
        id="c_paths", kind="route_present", router="R2", params={"min_paths": 3}
    )
    results, verdict = run_all([check_min_paths], session)
    assert verdict is False

    # Missing next hops include
    check_hops = Check(
        id="c_hops",
        kind="route_present",
        router="R2",
        params={"next_hops_include": ["10.99.99.99"]},
    )
    results, verdict = run_all([check_hops], session)
    assert verdict is False


def test_u3_3_route_absent_pass_and_fail() -> None:
    """U3.3: route_absent passes when not in RIB, fails when present."""
    session = MagicMock()
    session.show.return_value = "% Network not in table\n"

    check = Check(id="c1", kind="route_absent", router="R1", prefix="192.168.99.0 255.255.255.0")
    results, verdict = run_all([check], session)
    assert verdict is True

    session.show.return_value = (
        "Routing entry for 192.168.99.0/24\n"
        '  Known via "connected", distance 0, metric 0 (connected)\n'
        "  * directly connected, via Loopback99\n"
    )
    results, verdict = run_all([check], session)
    assert verdict is False


def test_u3_3_route_next_hops() -> None:
    """U3.3: route_next_hops passes when must_include and must_exclude are respected."""
    session = MagicMock()
    session.show.return_value = (
        "Routing entry for 10.10.1.0/24\n"
        '  Known via "eigrp 100", distance 90, metric 1308160\n'
        "  Routing Descriptor Blocks:\n"
        "  * 10.1.12.1, via GigabitEthernet2\n"
    )

    # Pass
    check_pass = Check(
        id="c_hop",
        kind="route_next_hops",
        router="R2",
        params={"must_include": ["10.1.12.1"], "must_exclude": ["10.1.99.1"]},
    )
    results, verdict = run_all([check_pass], session)
    assert verdict is True

    # Fail: missing required
    check_missing = Check(
        id="c_miss",
        kind="route_next_hops",
        router="R2",
        params={"must_include": ["10.1.99.1"]},
    )
    results, verdict = run_all([check_missing], session)
    assert verdict is False

    # Fail: contains excluded
    check_excluded = Check(
        id="c_ex",
        kind="route_next_hops",
        router="R2",
        params={"must_exclude": ["10.1.12.1"]},
    )
    results, verdict = run_all([check_excluded], session)
    assert verdict is False

    # Fail: route not in table
    session.show.return_value = "% Network not in table\n"
    results, verdict = run_all([check_pass], session)
    assert verdict is False


def test_u3_3_neighbor_up_pass_and_fail() -> None:
    """U3.3: neighbor_up passes when neighbor is up (or OSPF FULL), fails otherwise."""
    session = MagicMock()

    # OSPF pass & fail
    session.show.return_value = (
        "Neighbor ID     Pri   State           Dead Time   Address         Interface\n"
        "10.1.24.2         1   FULL/BDR        00:00:33    10.1.24.2       GigabitEthernet3\n"
    )
    check_ospf_pass = Check(
        id="c1",
        kind="neighbor_up",
        router="R4",
        params={"protocol": "ospf", "address": "10.1.24.2"},
    )
    results, verdict = run_all([check_ospf_pass], session)
    assert verdict is True

    check_ospf_fail = Check(
        id="c2",
        kind="neighbor_up",
        router="R4",
        params={"protocol": "ospf", "address": "10.1.99.99"},
    )
    results, verdict = run_all([check_ospf_fail], session)
    assert verdict is False

    # EIGRP pass & fail
    session.show.return_value = (
        "EIGRP-IPv4 Neighbors for AS(100)\n"
        "H   Address                 Interface              Hold Uptime   SRTT   RTO  Q  Seq\n"
        "0   10.1.12.2               Gi2                      14 00:32:15   10   200  0  18\n"
    )
    check_eigrp_pass = Check(
        id="c3",
        kind="neighbor_up",
        router="R1",
        params={"protocol": "eigrp", "address": "10.1.12.2"},
    )
    results, verdict = run_all([check_eigrp_pass], session)
    assert verdict is True

    check_eigrp_fail = Check(
        id="c4",
        kind="neighbor_up",
        router="R1",
        params={"protocol": "eigrp", "address": "10.1.99.99"},
    )
    results, verdict = run_all([check_eigrp_fail], session)
    assert verdict is False


def test_u3_3_config_contains_and_absent() -> None:
    """U3.3: config_contains and config_absent verify presence/absence in section."""
    session = MagicMock()
    session.show.return_value = (
        "router eigrp 100\n"
        " network 10.10.1.0 0.0.0.255\n"
        " redistribute ospf 1 metric 10000 100 255 1 1500 route-map RM_O_TO_E\n"
    )

    check_contains = Check(
        id="c1",
        kind="config_contains",
        router="R2",
        params={"section": "router eigrp", "regex": r"redistribute ospf 1"},
    )
    results, verdict = run_all([check_contains], session)
    assert verdict is True

    # Contains fail
    check_contains_fail = Check(
        id="c_fail",
        kind="config_contains",
        router="R2",
        params={"section": "router eigrp", "regex": r"redistribute bgp"},
    )
    results, verdict = run_all([check_contains_fail], session)
    assert verdict is False

    check_absent = Check(
        id="c2",
        kind="config_absent",
        router="R2",
        params={"section": "router eigrp", "regex": r"redistribute rip"},
    )
    results, verdict = run_all([check_absent], session)
    assert verdict is True

    # Absent fail
    check_absent_fail = Check(
        id="c_abs_fail",
        kind="config_absent",
        router="R2",
        params={"section": "router eigrp", "regex": r"redistribute ospf 1"},
    )
    results, verdict = run_all([check_absent_fail], session)
    assert verdict is False


def test_u3_3_routemap_clause() -> None:
    """U3.3: routemap_clause checks name, seq, action, match, and set."""
    session = MagicMock()
    session.show.return_value = (
        "route-map RM_TEST, permit, sequence 10\n"
        "  Match clauses:\n"
        "    tag 100\n"
        "  Set clauses:\n"
        "    metric 20\n"
    )

    # Pass
    check_pass = Check(
        id="c_rm",
        kind="routemap_clause",
        router="R2",
        params={
            "name": "RM_TEST",
            "seq": 10,
            "action": "permit",
            "match": {"tag": "100"},
            "set": {"metric": "20"},
        },
    )
    results, verdict = run_all([check_pass], session)
    assert verdict is True

    # Fail: clause not found
    check_missing = Check(
        id="c_rm_miss",
        kind="routemap_clause",
        router="R2",
        params={"name": "RM_MISSING", "seq": 10, "action": "permit"},
    )
    results, verdict = run_all([check_missing], session)
    assert verdict is False

    # Fail: match mismatch
    check_bad_match = Check(
        id="c_rm_bad_match",
        kind="routemap_clause",
        router="R2",
        params={"name": "RM_TEST", "seq": 10, "action": "permit", "match": {"tag": "999"}},
    )
    results, verdict = run_all([check_bad_match], session)
    assert verdict is False

    # Fail: set mismatch
    check_bad_set = Check(
        id="c_rm_bad_set",
        kind="routemap_clause",
        router="R2",
        params={"name": "RM_TEST", "seq": 10, "action": "permit", "set": {"metric": "999"}},
    )
    results, verdict = run_all([check_bad_set], session)
    assert verdict is False


def test_u3_3_ping() -> None:
    """U3.3: ping passes when success rate meets threshold, fails otherwise."""
    session = MagicMock()

    # Pass
    session.show.return_value = (
        "Sending 5, 100-byte ICMP Echos... \nSuccess rate is 100 percent (5/5)\n"
    )
    check_pass = Check(
        id="c_ping",
        kind="ping",
        router="R1",
        params={"source": "10.10.1.1", "dest": "172.16.20.17", "min_success_pct": 80},
    )
    results, verdict = run_all([check_pass], session)
    assert verdict is True

    # Fail
    session.show.return_value = (
        "Sending 5, 100-byte ICMP Echos... \nSuccess rate is 0 percent (0/5)\n"
    )
    results, verdict = run_all([check_pass], session)
    assert verdict is False


def test_u3_4_stable_detects_flapping_and_constant_with_fake_clock() -> None:
    """U3.4: stable check detects route flapping and passes on stable routes using FakeClock."""
    clock = FakeClock()
    session = MagicMock()

    # Flapping output: first 2 samples present, 3rd sample absent
    session.show.side_effect = [
        'Routing entry for 10.10.1.0/24\n  Known via "eigrp 100", distance 90, metric 1308160\n',
        'Routing entry for 10.10.1.0/24\n  Known via "eigrp 100", distance 90, metric 1308160\n',
        "% Network not in table\n",
    ]

    check = Check(
        id="c_stable",
        kind="stable",
        router="R1",
        prefix="10.10.1.0 255.255.255.0",
        params={"samples": 3, "interval_s": 2.0},
    )
    results, verdict = run_all([check], session, clock=clock)
    assert verdict is False
    assert "not stable" in results[0].message.lower() or "flip" in results[0].message.lower()
    assert clock.now() >= 4.0

    # Constant output: passes
    session.show.side_effect = None
    session.show.return_value = (
        'Routing entry for 10.10.1.0/24\n  Known via "eigrp 100", distance 90, metric 1308160\n'
    )
    results, verdict = run_all([check], session, clock=clock)
    assert verdict is True
    assert results[0].passed is True


def test_u3_5_baseline_guard() -> None:
    """U3.5: Baseline guard test (skipped until fault YAML catalog exists in Phase 4)."""
    from pathlib import Path

    catalog_dir = Path("src/t2t/faults/catalog")
    if not catalog_dir.exists() or not list(catalog_dir.glob("*.yaml")):
        pytest.skip(
            "Skipped in Phase 3: No fault catalog YAML files exist yet (enabled in Phase 4)."
        )
