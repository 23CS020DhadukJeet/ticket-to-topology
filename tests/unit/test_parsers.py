"""Unit tests U3.1 and U3.2 for router output parsers."""

from pathlib import Path

from t2t.parsers.config import parse_section
from t2t.parsers.neighbors import parse_eigrp_neighbors, parse_ospf_neighbors
from t2t.parsers.route import parse_route_detail
from t2t.parsers.routemap import parse_route_maps


def test_u3_1_parse_route_detail() -> None:
    """U3.1: parse_route_detail extracts route attributes and next hops."""
    text_eigrp = Path("tests/synthetic/routes/eigrp_ext.txt").read_text(encoding="utf-8")
    route = parse_route_detail(text_eigrp)

    assert route is not None
    assert route.prefix == "172.16.10.0/24"
    assert route.protocol == "eigrp"
    assert route.distance == 170
    assert route.metric == 25628160
    assert "external" in route.route_type
    assert route.tag == 200
    assert len(route.next_hops) == 2
    assert route.next_hops[0].ip == "10.1.12.2"
    assert route.next_hops[0].interface == "GigabitEthernet2"
    assert route.next_hops[0].from_ip == "10.1.12.2"

    text_ospf = Path("tests/synthetic/routes/ospf_ext2.txt").read_text(encoding="utf-8")
    route_ospf = parse_route_detail(text_ospf)
    assert route_ospf is not None
    assert route_ospf.prefix == "10.10.1.0/24"
    assert route_ospf.protocol == "ospf"
    assert route_ospf.distance == 110
    assert route_ospf.tag == 100
    assert len(route_ospf.next_hops) == 2


def test_u3_1_parse_neighbors() -> None:
    """U3.1: parse_eigrp_neighbors and parse_ospf_neighbors extract neighbor records."""
    eigrp_text = Path("tests/synthetic/neighbors/eigrp_neighbors.txt").read_text(encoding="utf-8")
    eigrp_nbrs = parse_eigrp_neighbors(eigrp_text)
    assert len(eigrp_nbrs) == 2
    assert eigrp_nbrs[0].address == "10.1.13.2"
    assert eigrp_nbrs[0].interface == "Gi3"
    assert eigrp_nbrs[1].address == "10.1.12.2"

    ospf_text = Path("tests/synthetic/neighbors/ospf_neighbors.txt").read_text(encoding="utf-8")
    ospf_nbrs = parse_ospf_neighbors(ospf_text)
    assert len(ospf_nbrs) == 2
    assert ospf_nbrs[0].address == "10.1.24.2"
    assert "FULL" in ospf_nbrs[0].state
    assert ospf_nbrs[0].interface == "GigabitEthernet3"


def test_u3_1_parse_route_maps() -> None:
    """U3.1: parse_route_maps extracts route-map clauses."""
    rm_text = Path("tests/synthetic/routemaps/routemap.txt").read_text(encoding="utf-8")
    clauses = parse_route_maps(rm_text)
    assert len(clauses) == 2

    assert clauses[0].name == "RM_EIGRP_TO_OSPF"
    assert clauses[0].action == "deny"
    assert clauses[0].seq == 10
    assert clauses[0].match.get("tag") == "200"

    assert clauses[1].name == "RM_EIGRP_TO_OSPF"
    assert clauses[1].action == "permit"
    assert clauses[1].seq == 20
    assert clauses[1].set.get("tag") == "100"


def test_u3_1_parse_section() -> None:
    """U3.1: parse_section extracts config blocks by keyword."""
    cfg_text = Path("tests/synthetic/configs/running_config_section.txt").read_text(
        encoding="utf-8"
    )
    sections = parse_section(cfg_text, "router")
    assert "router eigrp 100" in sections
    assert "redistribute ospf 1" in sections["router eigrp 100"]
    assert "router ospf 1" in sections
    assert "redistribute eigrp 100" in sections["router ospf 1"]


def test_u3_2_parsers_never_raise_on_garbage() -> None:
    """U3.2: parsers return None or [] on garbage, empty, or truncated input without raising."""
    garbage_inputs = [
        "",
        "   ",
        "Invalid command at '^' marker",
        "% Incomplete command",
        "% Network not in table",
        "random garbled garbage \x00\x01\x02 !!!",
        "Router#",
    ]

    for garbage in garbage_inputs:
        assert parse_route_detail(garbage) is None
        assert parse_eigrp_neighbors(garbage) == []
        assert parse_ospf_neighbors(garbage) == []
        assert parse_route_maps(garbage) == []
        assert parse_section(garbage, "router") == {}
