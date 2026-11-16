"""Integration test I3.1 for routing table oracle verification.

NOTE: Requires live 4-router lab and is excluded by default.
Run with: pytest -m lab
"""

import pytest

from t2t.devices.session import DeviceSession
from t2t.parsers.route import parse_route_detail

# Expected oracle attributes on the healthy lab baseline
ORACLE_CHECKS = [
    # R1 Branch
    (
        "R1",
        "172.16.10.0 255.255.255.0",
        {"protocol": "eigrp", "distance": 170, "tag": 200, "paths": 2},
    ),
    (
        "R1",
        "172.16.20.16 255.255.255.240",
        {"protocol": "eigrp", "distance": 170, "tag": 200, "paths": 2},
    ),
    # R2 ASBR-1
    ("R2", "10.10.1.0 255.255.255.0", {"protocol": "eigrp", "distance": 90}),
    ("R2", "10.10.2.0 255.255.255.0", {"protocol": "eigrp", "distance": 90}),
    ("R2", "10.10.99.0 255.255.255.0", {"protocol": "eigrp", "distance": 170}),
    ("R2", "172.16.10.0 255.255.255.0", {"protocol": "ospf", "distance": 110}),
    # R3 ASBR-2
    ("R3", "10.10.1.0 255.255.255.0", {"protocol": "eigrp", "distance": 90}),
    ("R3", "10.10.2.0 255.255.255.0", {"protocol": "eigrp", "distance": 90}),
    ("R3", "10.10.99.0 255.255.255.0", {"protocol": "eigrp", "distance": 170}),
    ("R3", "172.16.10.0 255.255.255.0", {"protocol": "ospf", "distance": 110}),
    # R4 HQ ABR
    (
        "R4",
        "10.10.1.0 255.255.255.0",
        {"protocol": "ospf", "distance": 110, "tag": 100, "paths": 2},
    ),
    (
        "R4",
        "10.10.2.0 255.255.255.0",
        {"protocol": "ospf", "distance": 110, "tag": 100, "paths": 2},
    ),
    (
        "R4",
        "10.10.99.0 255.255.255.0",
        {"protocol": "ospf", "distance": 110, "tag": 100, "paths": 2},
    ),
]


@pytest.mark.lab
def test_i3_1_oracle_baseline_prefixes() -> None:
    """I3.1 (lab): Parse every baseline prefix vs the oracle table."""
    with DeviceSession(read_only=True) as session:
        for router, prefix_cmd, expected in ORACLE_CHECKS:
            out = session.show(router, f"show ip route {prefix_cmd}")
            route = parse_route_detail(out)
            assert route is not None, f"{router}: prefix {prefix_cmd} not found in routing table."

            if "protocol" in expected:
                exp_p = expected["protocol"]
                assert route.protocol.lower() == exp_p.lower(), (
                    f"{router}: expected protocol {exp_p}, observed {route.protocol}."
                )
            if "distance" in expected:
                exp_d = expected["distance"]
                assert route.distance == exp_d, (
                    f"{router}: expected distance {exp_d}, observed {route.distance}."
                )
            if "tag" in expected:
                exp_t = expected["tag"]
                assert route.tag == exp_t, f"{router}: expected tag {exp_t}, observed {route.tag}."
            if "paths" in expected:
                exp_paths = expected["paths"]
                assert len(route.next_hops) >= exp_paths, (
                    f"{router}: expected >= {exp_paths} next hops, observed {len(route.next_hops)}."
                )
