"""Parsers for EIGRP and OSPF neighbor tables."""

import re

from t2t.models import Neighbor


def parse_eigrp_neighbors(text: str) -> list[Neighbor]:
    """Parse 'show ip eigrp neighbors' into a list of Neighbor models.

    Never raises an exception on bad/empty/garbage input.
    """
    if not text or not isinstance(text, str):
        return []

    neighbors: list[Neighbor] = []
    # EIGRP header ends with "Q Seq" or line starts with integer handle H
    # Example: 0 10.1.12.2 Gi2 14 00:32:15 10 200 0 18
    row_pattern = re.compile(
        r"^\s*\d+\s+([0-9\.]+)\s+([a-zA-Z0-9\/\.\-]+)\s+\d+\s+([0-9\:]+)",
        re.MULTILINE,
    )

    for match in row_pattern.finditer(text):
        address = match.group(1)
        interface = match.group(2)
        neighbors.append(Neighbor(address=address, interface=interface, state="UP"))

    return neighbors


def parse_ospf_neighbors(text: str) -> list[Neighbor]:
    """Parse 'show ip ospf neighbor' into a list of Neighbor models.

    Never raises an exception on bad/empty/garbage input.
    """
    if not text or not isinstance(text, str):
        return []

    neighbors: list[Neighbor] = []
    # Example: 10.1.24.2 1 FULL/BDR 00:00:33 10.1.24.2 GigabitEthernet3
    row_pattern = re.compile(
        r"^\s*([0-9\.]+)\s+\d+\s+([A-Z0-9_\/\-]+)\s+[0-9\:]+\s+([0-9\.]+)\s+([a-zA-Z0-9\/\.\-]+)",
        re.MULTILINE,
    )

    for match in row_pattern.finditer(text):
        state = match.group(2)
        address = match.group(3)
        interface = match.group(4)
        neighbors.append(Neighbor(address=address, interface=interface, state=state))

    return neighbors
