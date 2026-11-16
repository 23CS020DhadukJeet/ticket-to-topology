"""Unit tests U2.1 for command slugification."""

import hashlib
import re

from t2t.devices.slug import slug

PHASE_1_COMMANDS = [
    "show version",
    "show ip route",
    "show ip route 10.10.1.0 255.255.255.0",
    "show ip route 10.10.2.0 255.255.255.0",
    "show ip route 10.10.99.0 255.255.255.0",
    "show ip route 172.16.10.0 255.255.255.0",
    "show ip route 172.16.20.16 255.255.255.240",
    "show ip protocols",
    "show ip eigrp neighbors",
    "show ip ospf neighbor",
    "show route-map",
    "show running-config | section router|route-map|prefix-list",
]


def test_u2_1_slug_deterministic_and_collision_free() -> None:
    """U2.1: slug is deterministic and collision-free on the Phase 1 command list."""
    slugs = [slug(cmd) for cmd in PHASE_1_COMMANDS]
    # Check deterministic
    slugs_repeat = [slug(cmd) for cmd in PHASE_1_COMMANDS]
    assert slugs == slugs_repeat

    # Check collision-free
    assert len(slugs) == len(set(slugs))

    # All slugs should only contain lowercase alphanumerics and underscores
    for s in slugs:
        assert re.match(r"^[a-z0-9_]+$", s)
        assert not s.startswith("_")
        assert not s.endswith("_")
        assert len(s) <= 80


def test_slug_formatting() -> None:
    """Check slug formatting for pipe and multiple non-alphanumeric runs."""
    assert slug("show ip route") == "show_ip_route"
    assert slug("show running-config | section router") == "show_running_config_section_router"


def test_slug_long_truncation() -> None:
    """Check that commands longer than 80 chars are truncated with sha1 digest."""
    long_cmd = "show " + "x" * 100
    s = slug(long_cmd)
    expected_hash = hashlib.sha1(long_cmd.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]
    assert len(s) == 70 + 1 + 8
    assert s.endswith(f"_{expected_hash}")
