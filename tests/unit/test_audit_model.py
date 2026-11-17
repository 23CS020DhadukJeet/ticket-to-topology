"""Unit tests for Phase 7 DeviceModel parser."""

from pathlib import Path

from t2t.audit.model import (
    DeviceModel,
    parse_device_model,
)


def test_parse_device_model_baseline_r2() -> None:
    """Verify parsing of baseline R2 running configuration."""
    cfg_path = Path("tests/synthetic/audit/baseline/R2.cfg")
    text = cfg_path.read_text(encoding="utf-8")
    model = parse_device_model("R2", text)

    assert isinstance(model, DeviceModel)
    assert model.name == "R2"
    assert len(model.config_sha256) == 64

    # Routing processes: EIGRP 100 and OSPF 1
    assert len(model.routing_processes) == 2
    eigrp = next(p for p in model.routing_processes if p.protocol == "eigrp")
    ospf = next(p for p in model.routing_processes if p.protocol == "ospf")

    assert eigrp.process_id == "100"
    assert len(eigrp.redistributions) == 1
    r_ospf = eigrp.redistributions[0]
    assert r_ospf.source_protocol == "ospf"
    assert r_ospf.source_id == "1"
    assert r_ospf.metric == "10000 100 255 1 1500"
    assert r_ospf.route_map == "OSPF-TO-EIGRP"

    assert ospf.process_id == "1"
    assert ospf.router_id == "2.2.2.2"
    assert ospf.ospf_distance_external == 171
    assert len(ospf.redistributions) == 1
    r_eigrp = ospf.redistributions[0]
    assert r_eigrp.source_protocol == "eigrp"
    assert r_eigrp.source_id == "100"
    assert r_eigrp.subnets is True
    assert r_eigrp.route_map == "EIGRP-TO-OSPF"

    # Route maps: EIGRP-TO-OSPF and OSPF-TO-EIGRP
    assert "EIGRP-TO-OSPF" in model.route_maps
    assert "OSPF-TO-EIGRP" in model.route_maps
    rm_eigrp_to_ospf = model.route_maps["EIGRP-TO-OSPF"]
    assert len(rm_eigrp_to_ospf) == 2
    clause10 = rm_eigrp_to_ospf[0]
    assert clause10.action == "deny"
    assert clause10.sequence == 10
    assert 200 in clause10.match_tags

    clause20 = rm_eigrp_to_ospf[1]
    assert clause20.action == "permit"
    assert clause20.sequence == 20
    assert clause20.set_tag == 100

    # Prefix list
    assert "HQ-NETS" in model.prefix_lists
