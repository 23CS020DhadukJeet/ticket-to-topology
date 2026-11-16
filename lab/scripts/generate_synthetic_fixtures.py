"""Generate synthetic offline demo fixtures for running without a virtual machine.

Generates complete, deterministic fixtures under tests/synthetic/fixtures/
matching the Phase 1 Baseline Oracle specifications.
"""

from pathlib import Path

from t2t.devices.slug import slug

SYNTHETIC_ROOT = Path("tests/synthetic/fixtures")

VERSION_OUTPUT = """Cisco IOS XE Software, Version 17.09.04a
Cisco IOS Software [Cupertino], Virtual XE Software, Version 17.9.4a, RELEASE SOFTWARE (fc2)
Technical Support: http://www.cisco.com/techsupport
Copyright (c) 1986-2023 by Cisco Systems, Inc.
Compiled Wed 22-Mar-23 04:36 by mcpre
ROM: IOS-XE ROMMON

{router} uptime is 2 hours, 15 minutes
Uptime for this control processor is 2 hours, 18 minutes
System returned to ROM by reload
System image file is "bootflash:packages.conf"
Last reload reason: Normal Reload
"""

DIR_GOLDEN_OUTPUT = """Directory of flash:/golden.cfg

12345  -rw-        3412  Nov 17 2026 00:00:00 +00:00  golden.cfg

1073741824 bytes total (789456789 bytes free)
"""

ARCHIVE_OUTPUT = """archive
 path flash:archive
 maximum 14
 write-memory
"""

VRF_OUTPUT = """  Name                             Default RD            Protocols   Interfaces
  MGMT                             1:1                   ipv4,ipv6   GigabitEthernet1
"""

EIGRP_NBR_R1 = """EIGRP-IPv4 Neighbors for AS(100)
H   Address                 Interface              Hold Uptime   SRTT   RTO  Q   Seq
                                                   (sec)         (ms)       Cnt  Num
0   10.1.12.2               Gi2                      12 02:14:20   12   200  0   45
1   10.1.13.2               Gi3                      14 02:14:15   15   200  0   41
"""

EIGRP_NBR_R2 = """EIGRP-IPv4 Neighbors for AS(100)
H   Address                 Interface              Hold Uptime   SRTT   RTO  Q   Seq
                                                   (sec)         (ms)       Cnt  Num
0   10.1.12.1               Gi2                      13 02:14:20   14   200  0   46
"""

EIGRP_NBR_R3 = """EIGRP-IPv4 Neighbors for AS(100)
H   Address                 Interface              Hold Uptime   SRTT   RTO  Q   Seq
                                                   (sec)         (ms)       Cnt  Num
0   10.1.13.1               Gi2                      11 02:14:15   11   200  0   42
"""

EIGRP_NBR_EMPTY = """EIGRP-IPv4 Neighbors for AS(100)
"""

OSPF_NBR_EMPTY = """Neighbor ID     Pri   State           Dead Time   Address         Interface
"""

OSPF_NBR_R2 = """Neighbor ID     Pri   State           Dead Time   Address         Interface
4.4.4.4           1   FULL/DR         00:00:36    10.1.24.2       GigabitEthernet3
"""

OSPF_NBR_R3 = """Neighbor ID     Pri   State           Dead Time   Address         Interface
4.4.4.4           1   FULL/DR         00:00:35    10.1.34.2       GigabitEthernet3
"""

OSPF_NBR_R4 = """Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   FULL/BDR        00:00:34    10.1.24.1       GigabitEthernet2
3.3.3.3           1   FULL/BDR        00:00:33    10.1.34.1       GigabitEthernet3
"""

ROUTE_MAP_ASBR = """route-map EIGRP-TO-OSPF, deny, sequence 10
  Match clauses:
    tag 200
  Set clauses:
route-map EIGRP-TO-OSPF, permit, sequence 20
  Match clauses:
  Set clauses:
    tag 100
route-map OSPF-TO-EIGRP, deny, sequence 10
  Match clauses:
    tag 100
  Set clauses:
route-map OSPF-TO-EIGRP, permit, sequence 20
  Match clauses:
    ip address prefix-list HQ-NETS
  Set clauses:
    tag 200
"""

ROUTE_MAP_ASBR_T1 = """route-map EIGRP-TO-OSPF, permit, sequence 20
  Match clauses:
  Set clauses:
    tag 100
route-map OSPF-TO-EIGRP, permit, sequence 20
  Match clauses:
    ip address prefix-list HQ-NETS
  Set clauses:
    tag 200
"""

ROUTE_MAP_R1 = """route-map VENDOR-CONN, permit, sequence 10
  Match clauses:
    interface Loopback99
  Set clauses:
"""

SECT_R1 = """router eigrp 100
 network 10.10.1.0 0.0.0.255
 network 10.10.2.0 0.0.0.255
 network 10.1.12.0 0.0.0.255
 network 10.1.13.0 0.0.0.255
 redistribute connected route-map VENDOR-CONN
route-map VENDOR-CONN permit 10
 match interface Loopback99
"""

SECT_R2 = """router eigrp 100
 network 10.1.12.0 0.0.0.255
 redistribute ospf 1 metric 10000 100 255 1 1500 route-map OSPF-TO-EIGRP
router ospf 1
 router-id 2.2.2.2
 network 10.1.24.0 0.0.0.255 area 0
 redistribute eigrp 100 subnets route-map EIGRP-TO-OSPF
 distance ospf external 171
ip prefix-list HQ-NETS seq 10 permit 172.16.10.0/24
ip prefix-list HQ-NETS seq 20 permit 172.16.20.16/28
route-map EIGRP-TO-OSPF deny 10
 match tag 200
route-map EIGRP-TO-OSPF permit 20
 set tag 100
route-map OSPF-TO-EIGRP deny 10
 match tag 100
route-map OSPF-TO-EIGRP permit 20
 match ip address prefix-list HQ-NETS
 set tag 200
"""

SECT_R3 = """router eigrp 100
 network 10.1.13.0 0.0.0.255
 redistribute ospf 1 metric 10000 100 255 1 1500 route-map OSPF-TO-EIGRP
router ospf 1
 router-id 3.3.3.3
 network 10.1.34.0 0.0.0.255 area 0
 redistribute eigrp 100 subnets route-map EIGRP-TO-OSPF
 distance ospf external 171
ip prefix-list HQ-NETS seq 10 permit 172.16.10.0/24
ip prefix-list HQ-NETS seq 20 permit 172.16.20.16/28
route-map EIGRP-TO-OSPF deny 10
 match tag 200
route-map EIGRP-TO-OSPF permit 20
 set tag 100
route-map OSPF-TO-EIGRP deny 10
 match tag 100
route-map OSPF-TO-EIGRP permit 20
 match ip address prefix-list HQ-NETS
 set tag 200
"""

SECT_R4 = """router ospf 1
 router-id 4.4.4.4
 network 10.1.24.0 0.0.0.255 area 0
 network 10.1.34.0 0.0.0.255 area 0
 network 172.16.10.0 0.0.0.255 area 0
 network 172.16.20.16 0.0.0.15 area 0
"""

ROUTE_NOT_IN_TABLE = "% Network not in table\n"


def _route_connected(prefix: str, intf: str) -> str:
    return (
        f"Routing entry for {prefix}\n"
        f'  Known via "connected", distance 0, metric 0 (connected, via interface)\n'
        f"  Routing Descriptor Blocks:\n"
        f"  * directly connected, via {intf}\n"
        f"      Route count is 1, list sub-block of 1\n"
    )


def _route_eigrp(prefix: str, dist: int, nh: str, intf: str, tag: int | None = None) -> str:
    tag_str = f"  Route tag {tag}\n" if tag else ""
    rtype = "internal" if dist == 90 else "external"
    return (
        f"Routing entry for {prefix}\n"
        f'  Known via "eigrp 100", distance {dist}, metric 1308160, type {rtype}\n'
        f"{tag_str}"
        f"  Routing Descriptor Blocks:\n"
        f"  * {nh}, from {nh}, 02:14:20 ago, via {intf}\n"
        f"      Route metric is 1308160, traffic share count is 1\n"
    )


def _route_eigrp_dual(
    prefix: str, dist: int, nh1: str, if1: str, nh2: str, if2: str, tag: int | None = None
) -> str:
    tag_str = f"  Route tag {tag}\n" if tag else ""
    return (
        f"Routing entry for {prefix}\n"
        f'  Known via "eigrp 100", distance {dist}, metric 1308160, type external\n'
        f"{tag_str}"
        f"  Routing Descriptor Blocks:\n"
        f"  * {nh1}, from {nh1}, 02:14:20 ago, via {if1}\n"
        f"      Route metric is 1308160, traffic share count is 1\n"
        f"  * {nh2}, from {nh2}, 02:14:20 ago, via {if2}\n"
        f"      Route metric is 1308160, traffic share count is 1\n"
    )


def _route_ospf(
    prefix: str, dist: int, rtype: str, nh: str, intf: str, tag: int | None = None
) -> str:
    tag_str = f"  Route tag {tag}\n" if tag else ""
    return (
        f"Routing entry for {prefix}\n"
        f'  Known via "ospf 1", distance {dist}, metric 11, type {rtype}\n'
        f"{tag_str}"
        f"  Routing Descriptor Blocks:\n"
        f"  * {nh}, from {nh}, 02:14:00 ago, via {intf}\n"
        f"      Route metric is 11, traffic share count is 1\n"
    )


def _route_ospf_dual(
    prefix: str, dist: int, nh1: str, if1: str, nh2: str, if2: str, tag: int | None = None
) -> str:
    tag_str = f"  Route tag {tag}\n" if tag else ""
    return (
        f"Routing entry for {prefix}\n"
        f'  Known via "ospf 1", distance {dist}, metric 20, type extern 2, forward metric 1\n'
        f"{tag_str}"
        f"  Routing Descriptor Blocks:\n"
        f"  * {nh1}, from 2.2.2.2, 02:14:00 ago, via {if1}\n"
        f"      Route metric is 20, traffic share count is 1\n"
        f"  * {nh2}, from 3.3.3.3, 02:14:00 ago, via {if2}\n"
        f"      Route metric is 20, traffic share count is 1\n"
    )


def _write_route(
    scenario: str, router: str, prefix_cidr: str, prefix_mask: str, content: str
) -> None:
    """Write route output under CIDR, subnet mask, and bare prefix slugs."""
    r_dir = SYNTHETIC_ROOT / scenario / router
    r_dir.mkdir(parents=True, exist_ok=True)
    slugs = [
        slug(f"show ip route {prefix_cidr}"),
        slug(f"show ip route {prefix_mask}"),
        slug(f"show ip route {prefix_cidr.split('/')[0]}"),
    ]
    for s in set(slugs):
        (r_dir / f"{s}.txt").write_text(content, encoding="utf-8")


def generate_baseline_fixtures() -> None:
    """Generate all baseline scenario synthetic fixtures."""
    routers = ["R1", "R2", "R3", "R4"]
    for r in routers:
        r_dir = SYNTHETIC_ROOT / "baseline" / r
        r_dir.mkdir(parents=True, exist_ok=True)

        (r_dir / "show_version.txt").write_text(VERSION_OUTPUT.format(router=r), encoding="utf-8")
        (r_dir / "dir_flash_golden_cfg.txt").write_text(DIR_GOLDEN_OUTPUT, encoding="utf-8")
        (r_dir / "show_running_config_section_archive.txt").write_text(
            ARCHIVE_OUTPUT, encoding="utf-8"
        )
        (r_dir / "show_vrf.txt").write_text(VRF_OUTPUT, encoding="utf-8")
        (r_dir / "show_ip_route.txt").write_text(
            "Codes: C - connected, S - static, R - RIP, M - mobile, B - BGP\n", encoding="utf-8"
        )
        (r_dir / "show_ip_protocols.txt").write_text(
            'Routing Protocol is "eigrp 100"\nRouting Protocol is "ospf 1"\n', encoding="utf-8"
        )

    # EIGRP neighbors
    (SYNTHETIC_ROOT / "baseline/R1/show_ip_eigrp_neighbors.txt").write_text(
        EIGRP_NBR_R1, encoding="utf-8"
    )
    (SYNTHETIC_ROOT / "baseline/R2/show_ip_eigrp_neighbors.txt").write_text(
        EIGRP_NBR_R2, encoding="utf-8"
    )
    (SYNTHETIC_ROOT / "baseline/R3/show_ip_eigrp_neighbors.txt").write_text(
        EIGRP_NBR_R3, encoding="utf-8"
    )
    (SYNTHETIC_ROOT / "baseline/R4/show_ip_eigrp_neighbors.txt").write_text(
        EIGRP_NBR_EMPTY, encoding="utf-8"
    )

    # OSPF neighbors
    (SYNTHETIC_ROOT / "baseline/R1/show_ip_ospf_neighbor.txt").write_text(
        OSPF_NBR_EMPTY, encoding="utf-8"
    )
    (SYNTHETIC_ROOT / "baseline/R2/show_ip_ospf_neighbor.txt").write_text(
        OSPF_NBR_R2, encoding="utf-8"
    )
    (SYNTHETIC_ROOT / "baseline/R3/show_ip_ospf_neighbor.txt").write_text(
        OSPF_NBR_R3, encoding="utf-8"
    )
    (SYNTHETIC_ROOT / "baseline/R4/show_ip_ospf_neighbor.txt").write_text(
        OSPF_NBR_R4, encoding="utf-8"
    )

    # Route maps
    (SYNTHETIC_ROOT / "baseline/R1/show_route_map.txt").write_text(ROUTE_MAP_R1, encoding="utf-8")
    (SYNTHETIC_ROOT / "baseline/R1/show_route_map_vendor_conn.txt").write_text(
        ROUTE_MAP_R1, encoding="utf-8"
    )
    (SYNTHETIC_ROOT / "baseline/R2/show_route_map.txt").write_text(ROUTE_MAP_ASBR, encoding="utf-8")
    (SYNTHETIC_ROOT / "baseline/R2/show_route_map_eigrp_to_ospf.txt").write_text(
        ROUTE_MAP_ASBR, encoding="utf-8"
    )
    (SYNTHETIC_ROOT / "baseline/R2/show_route_map_ospf_to_eigrp.txt").write_text(
        ROUTE_MAP_ASBR, encoding="utf-8"
    )
    (SYNTHETIC_ROOT / "baseline/R3/show_route_map.txt").write_text(ROUTE_MAP_ASBR, encoding="utf-8")
    (SYNTHETIC_ROOT / "baseline/R3/show_route_map_eigrp_to_ospf.txt").write_text(
        ROUTE_MAP_ASBR, encoding="utf-8"
    )
    (SYNTHETIC_ROOT / "baseline/R3/show_route_map_ospf_to_eigrp.txt").write_text(
        ROUTE_MAP_ASBR, encoding="utf-8"
    )
    (SYNTHETIC_ROOT / "baseline/R4/show_route_map.txt").write_text("", encoding="utf-8")

    # Section configs
    sec_cmd_slug = slug("show running-config | section router|route-map|prefix-list")
    (SYNTHETIC_ROOT / f"baseline/R1/{sec_cmd_slug}.txt").write_text(SECT_R1, encoding="utf-8")
    (SYNTHETIC_ROOT / f"baseline/R2/{sec_cmd_slug}.txt").write_text(SECT_R2, encoding="utf-8")
    (SYNTHETIC_ROOT / f"baseline/R3/{sec_cmd_slug}.txt").write_text(SECT_R3, encoding="utf-8")
    (SYNTHETIC_ROOT / f"baseline/R4/{sec_cmd_slug}.txt").write_text(SECT_R4, encoding="utf-8")

    # Prefix 10.10.1.0/24
    _write_route(
        "baseline",
        "R1",
        "10.10.1.0/24",
        "10.10.1.0 255.255.255.0",
        _route_connected("10.10.1.0/24", "Loopback1"),
    )
    _write_route(
        "baseline",
        "R2",
        "10.10.1.0/24",
        "10.10.1.0 255.255.255.0",
        _route_eigrp("10.10.1.0/24", 90, "10.1.12.1", "GigabitEthernet2"),
    )
    _write_route(
        "baseline",
        "R3",
        "10.10.1.0/24",
        "10.10.1.0 255.255.255.0",
        _route_eigrp("10.10.1.0/24", 90, "10.1.13.1", "GigabitEthernet2"),
    )
    _write_route(
        "baseline",
        "R4",
        "10.10.1.0/24",
        "10.10.1.0 255.255.255.0",
        _route_ospf_dual(
            "10.10.1.0/24",
            110,
            "10.1.24.1",
            "GigabitEthernet2",
            "10.1.34.1",
            "GigabitEthernet3",
            tag=100,
        ),
    )

    # Prefix 10.10.2.0/24
    _write_route(
        "baseline",
        "R1",
        "10.10.2.0/24",
        "10.10.2.0 255.255.255.0",
        _route_connected("10.10.2.0/24", "Loopback2"),
    )
    _write_route(
        "baseline",
        "R2",
        "10.10.2.0/24",
        "10.10.2.0 255.255.255.0",
        _route_eigrp("10.10.2.0/24", 90, "10.1.12.1", "GigabitEthernet2"),
    )
    _write_route(
        "baseline",
        "R3",
        "10.10.2.0/24",
        "10.10.2.0 255.255.255.0",
        _route_eigrp("10.10.2.0/24", 90, "10.1.13.1", "GigabitEthernet2"),
    )
    _write_route(
        "baseline",
        "R4",
        "10.10.2.0/24",
        "10.10.2.0 255.255.255.0",
        _route_ospf_dual(
            "10.10.2.0/24",
            110,
            "10.1.24.1",
            "GigabitEthernet2",
            "10.1.34.1",
            "GigabitEthernet3",
            tag=100,
        ),
    )

    # Prefix 10.10.99.0/24
    _write_route(
        "baseline",
        "R1",
        "10.10.99.0/24",
        "10.10.99.0 255.255.255.0",
        _route_connected("10.10.99.0/24", "Loopback99"),
    )
    _write_route(
        "baseline",
        "R2",
        "10.10.99.0/24",
        "10.10.99.0 255.255.255.0",
        _route_eigrp("10.10.99.0/24", 170, "10.1.12.1", "GigabitEthernet2"),
    )
    _write_route(
        "baseline",
        "R3",
        "10.10.99.0/24",
        "10.10.99.0 255.255.255.0",
        _route_eigrp("10.10.99.0/24", 170, "10.1.13.1", "GigabitEthernet2"),
    )
    _write_route(
        "baseline",
        "R4",
        "10.10.99.0/24",
        "10.10.99.0 255.255.255.0",
        _route_ospf_dual(
            "10.10.99.0/24",
            110,
            "10.1.24.1",
            "GigabitEthernet2",
            "10.1.34.1",
            "GigabitEthernet3",
            tag=100,
        ),
    )

    # Prefix 172.16.10.0/24
    _write_route(
        "baseline",
        "R1",
        "172.16.10.0/24",
        "172.16.10.0 255.255.255.0",
        _route_eigrp_dual(
            "172.16.10.0/24",
            170,
            "10.1.12.2",
            "GigabitEthernet2",
            "10.1.13.2",
            "GigabitEthernet3",
            tag=200,
        ),
    )
    _write_route(
        "baseline",
        "R2",
        "172.16.10.0/24",
        "172.16.10.0 255.255.255.0",
        _route_ospf("172.16.10.0/24", 110, "inter area", "10.1.24.2", "GigabitEthernet3"),
    )
    _write_route(
        "baseline",
        "R3",
        "172.16.10.0/24",
        "172.16.10.0 255.255.255.0",
        _route_ospf("172.16.10.0/24", 110, "inter area", "10.1.34.2", "GigabitEthernet3"),
    )
    _write_route(
        "baseline",
        "R4",
        "172.16.10.0/24",
        "172.16.10.0 255.255.255.0",
        _route_connected("172.16.10.0/24", "Loopback10"),
    )

    # Prefix 172.16.20.16/28
    _write_route(
        "baseline",
        "R1",
        "172.16.20.16/28",
        "172.16.20.16 255.255.255.240",
        _route_eigrp_dual(
            "172.16.20.16/28",
            170,
            "10.1.12.2",
            "GigabitEthernet2",
            "10.1.13.2",
            "GigabitEthernet3",
            tag=200,
        ),
    )
    _write_route(
        "baseline",
        "R2",
        "172.16.20.16/28",
        "172.16.20.16 255.255.255.240",
        _route_ospf("172.16.20.16/28", 110, "inter area", "10.1.24.2", "GigabitEthernet3"),
    )
    _write_route(
        "baseline",
        "R3",
        "172.16.20.16/28",
        "172.16.20.16 255.255.255.240",
        _route_ospf("172.16.20.16/28", 110, "inter area", "10.1.34.2", "GigabitEthernet3"),
    )
    _write_route(
        "baseline",
        "R4",
        "172.16.20.16/28",
        "172.16.20.16 255.255.255.240",
        _route_connected("172.16.20.16/28", "Loopback20"),
    )

    print(f"Generated synthetic baseline fixtures under {SYNTHETIC_ROOT / 'baseline'}")


def generate_faulted_fixtures() -> None:
    """Generate synthetic fixtures for faulted scenarios (T1 through T10)."""
    # Fault T1: Loop prevention stripped on ASBRs R2 and R3
    (SYNTHETIC_ROOT / "faulted/T1/R2").mkdir(parents=True, exist_ok=True)
    (SYNTHETIC_ROOT / "faulted/T1/R3").mkdir(parents=True, exist_ok=True)
    for rm_slug in [
        "show_route_map",
        "show_route_map_eigrp_to_ospf",
        "show_route_map_ospf_to_eigrp",
    ]:
        (SYNTHETIC_ROOT / f"faulted/T1/R2/{rm_slug}.txt").write_text(
            ROUTE_MAP_ASBR_T1, encoding="utf-8"
        )
        (SYNTHETIC_ROOT / f"faulted/T1/R3/{rm_slug}.txt").write_text(
            ROUTE_MAP_ASBR_T1, encoding="utf-8"
        )

    # Fault T2: EIGRP seed metric omitted on R2 (R1 loses R2 path for 172.16.x)
    _write_route(
        "faulted/T2",
        "R1",
        "172.16.10.0/24",
        "172.16.10.0 255.255.255.0",
        _route_eigrp("172.16.10.0/24", 170, "10.1.13.2", "GigabitEthernet3", tag=200),
    )
    _write_route(
        "faulted/T2",
        "R1",
        "172.16.20.16/28",
        "172.16.20.16 255.255.255.240",
        _route_eigrp("172.16.20.16/28", 170, "10.1.13.2", "GigabitEthernet3", tag=200),
    )

    # Fault T3: OSPF external AD override removed on R3 (R3 uses OSPF E2 via R4)
    _write_route(
        "faulted/T3",
        "R3",
        "10.10.99.0/24",
        "10.10.99.0 255.255.255.0",
        (
            "Routing entry for 10.10.99.0/24\n"
            '  Known via "ospf 1", distance 110, metric 20, type extern 2, forward metric 1\n'
            "  Route tag 100\n"
            "  Routing Descriptor Blocks:\n"
            "  * 10.1.34.2, from 4.4.4.4, 00:01:10 ago, via GigabitEthernet3\n"
            "      Route metric is 20, traffic share count is 1\n"
        ),
    )

    # Fault T4: Subnets keyword omitted on R3 (R4 loses R3 path for subnets)
    _write_route(
        "faulted/T4",
        "R4",
        "10.10.1.0/24",
        "10.10.1.0 255.255.255.0",
        _route_ospf(
            "10.10.1.0/24",
            110,
            "extern 2, forward metric 1",
            "10.1.24.1",
            "GigabitEthernet2",
            tag=100,
        ),
    )
    _write_route(
        "faulted/T4",
        "R4",
        "10.10.2.0/24",
        "10.10.2.0 255.255.255.0",
        _route_ospf(
            "10.10.2.0/24",
            110,
            "extern 2, forward metric 1",
            "10.1.24.1",
            "GigabitEthernet2",
            tag=100,
        ),
    )

    # Fault T5: Prefix-list typo on R3 (R1 loses R3 path for 172.16.20.16/28)
    _write_route(
        "faulted/T5",
        "R1",
        "172.16.20.16/28",
        "172.16.20.16 255.255.255.240",
        _route_eigrp("172.16.20.16/28", 170, "10.1.12.2", "GigabitEthernet2", tag=200),
    )

    # Fault T6: Missing permit clause on R2 (R1 loses R2 path for HQ subnets)
    _write_route(
        "faulted/T6",
        "R1",
        "172.16.10.0/24",
        "172.16.10.0 255.255.255.0",
        _route_eigrp("172.16.10.0/24", 170, "10.1.13.2", "GigabitEthernet3", tag=200),
    )
    _write_route(
        "faulted/T6",
        "R1",
        "172.16.20.16/28",
        "172.16.20.16 255.255.255.240",
        _route_eigrp("172.16.20.16/28", 170, "10.1.13.2", "GigabitEthernet3", tag=200),
    )

    # Fault T7: EIGRP passive-interface on R2 (R2-R1 neighbor down, R1 single-path)
    (SYNTHETIC_ROOT / "faulted/T7/R2").mkdir(parents=True, exist_ok=True)
    (SYNTHETIC_ROOT / "faulted/T7/R2/show_ip_eigrp_neighbors.txt").write_text(
        EIGRP_NBR_EMPTY, encoding="utf-8"
    )
    _write_route(
        "faulted/T7",
        "R1",
        "172.16.10.0/24",
        "172.16.10.0 255.255.255.0",
        _route_eigrp("172.16.10.0/24", 170, "10.1.13.2", "GigabitEthernet3", tag=200),
    )

    # Fault T8: Metric-type 1 on R2 only (R4 prefers single E1 path via R2)
    _write_route(
        "faulted/T8",
        "R4",
        "10.10.1.0/24",
        "10.10.1.0 255.255.255.0",
        (
            "Routing entry for 10.10.1.0/24\n"
            '  Known via "ospf 1", distance 110, metric 20, type extern 1\n'
            "  Route tag 100\n"
            "  Routing Descriptor Blocks:\n"
            "  * 10.1.24.1, from 2.2.2.2, 02:14:00 ago, via GigabitEthernet2\n"
            "      Route metric is 20, traffic share count is 1\n"
        ),
    )

    # Fault T9: EIGRP MD5 mismatch on R3 (R3-R1 neighbor down, R1 single-path)
    (SYNTHETIC_ROOT / "faulted/T9/R3").mkdir(parents=True, exist_ok=True)
    (SYNTHETIC_ROOT / "faulted/T9/R3/show_ip_eigrp_neighbors.txt").write_text(
        EIGRP_NBR_EMPTY, encoding="utf-8"
    )
    _write_route(
        "faulted/T9",
        "R1",
        "172.16.10.0/24",
        "172.16.10.0 255.255.255.0",
        _route_eigrp("172.16.10.0/24", 170, "10.1.12.2", "GigabitEthernet2", tag=200),
    )

    # Fault T10: Wrong interface in connected-redistribution (vendor prefix missing)
    _write_route(
        "faulted/T10",
        "R2",
        "10.10.99.0/24",
        "10.10.99.0 255.255.255.0",
        ROUTE_NOT_IN_TABLE,
    )
    _write_route(
        "faulted/T10",
        "R4",
        "10.10.99.0/24",
        "10.10.99.0 255.255.255.0",
        ROUTE_NOT_IN_TABLE,
    )

    print(f"Generated synthetic faulted fixtures under {SYNTHETIC_ROOT / 'faulted'}")


if __name__ == "__main__":
    generate_baseline_fixtures()
    generate_faulted_fixtures()
