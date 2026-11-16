"""Parser for Cisco IOS-XE 'show ip route PREFIX MASK' detail output."""

import re

from t2t.models import NextHop, RouteDetail


def parse_route_detail(text: str) -> RouteDetail | None:
    """Parse detailed route output into a RouteDetail model.

    Returns None if prefix is not in routing table or output is invalid.
    Never raises an exception on bad/garbage/truncated input.
    """
    if not text or not isinstance(text, str):
        return None

    if "% Network not in table" in text or "% Subnet not in table" in text:
        return None

    prefix_match = re.search(r"Routing entry for\s+([0-9\.\/]+)", text, re.IGNORECASE)
    if not prefix_match:
        return None

    prefix = prefix_match.group(1)

    # Known via "eigrp 100", distance 170, metric 25628160, type external
    # Known via "connected", distance 0, metric 0 (connected)
    known_match = re.search(
        r'Known via "([^"]+)",\s*distance\s+(\d+),\s*metric\s+(\d+)(?:,\s*type\s+([^,\r\n]+))?',
        text,
        re.IGNORECASE,
    )

    if not known_match:
        # Fallback without quotes: Known via connected, distance 0, metric 0
        known_match = re.search(
            r"Known via ([^,]+),\s*distance\s+(\d+),\s*metric\s+(\d+)(?:,\s*type\s+([^,\r\n]+))?",
            text,
            re.IGNORECASE,
        )

    if not known_match:
        return None

    known_via = known_match.group(1).strip()
    protocol = known_via.split()[0].lower()
    distance = int(known_match.group(2))
    metric = int(known_match.group(3))
    route_type = (known_match.group(4) or "").strip()

    # Route tag
    tag_match = re.search(r"Route tag\s+(\d+)", text, re.IGNORECASE)
    tag = int(tag_match.group(1)) if tag_match else None

    # Advertised by
    advertised_by: list[str] = []
    for adv_match in re.finditer(r"Advertised by\s+([^\r\n]+)", text, re.IGNORECASE):
        advertised_by.append(adv_match.group(1).strip())

    # Routing Descriptor Blocks:
    #   * 10.1.12.2, from 10.1.12.2, 00:05:21 ago, via GigabitEthernet2
    #     10.1.13.2, from 10.1.13.2, 00:05:21 ago, via GigabitEthernet3
    #   * directly connected, via Loopback0
    next_hops: list[NextHop] = []
    hop_pattern = re.compile(
        r"^(?:\*\s*)?([0-9\.]+|directly connected),\s*"
        r"(?:from\s+([0-9\.]+),)?.*?via\s+([a-zA-Z0-9\/\.\-]+)",
        re.IGNORECASE,
    )

    for line in text.splitlines():
        line_clean = line.strip()
        if not line_clean:
            continue
        m = hop_pattern.match(line_clean)
        if m:
            hop_ip = m.group(1)
            from_ip = m.group(2) or hop_ip
            interface = m.group(3)
            next_hops.append(NextHop(ip=hop_ip, interface=interface, from_ip=from_ip))

    return RouteDetail(
        prefix=prefix,
        known_via=known_via,
        protocol=protocol,
        distance=distance,
        metric=metric,
        route_type=route_type,
        tag=tag,
        next_hops=next_hops,
        advertised_by=advertised_by,
    )
