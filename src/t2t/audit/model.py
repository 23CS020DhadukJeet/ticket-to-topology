"""Data models and Cisco IOS-XE configuration parser for audit engine."""

import hashlib
import re
from typing import Literal

from pydantic import BaseModel, Field


class Redistribution(BaseModel):
    """Parsed redistribute statement under a routing process."""

    source_protocol: str
    source_id: str | None = None
    metric: str | None = None
    subnets: bool = False
    metric_type: str | None = None
    route_map: str | None = None


class RoutingProcess(BaseModel):
    """Parsed routing process configuration (e.g. EIGRP, OSPF)."""

    protocol: str
    process_id: str
    router_id: str | None = None
    networks: list[str] = Field(default_factory=list)
    redistributions: list[Redistribution] = Field(default_factory=list)
    default_metric: str | None = None
    ospf_distance_external: int | None = None


class RouteMapClauseModel(BaseModel):
    """Parsed clause of a Cisco route-map."""

    name: str
    action: Literal["permit", "deny"]
    sequence: int
    match_tags: list[int] = Field(default_factory=list)
    set_tag: int | None = None
    match_prefix_lists: list[str] = Field(default_factory=list)
    match_acls: list[str] = Field(default_factory=list)
    match_interfaces: list[str] = Field(default_factory=list)
    set_metric: str | None = None
    raw_lines: list[str] = Field(default_factory=list)


class DeviceModel(BaseModel):
    """Complete parsed configuration model of an audited network device."""

    name: str
    raw_config: str
    config_sha256: str
    routing_processes: list[RoutingProcess] = Field(default_factory=list)
    route_maps: dict[str, list[RouteMapClauseModel]] = Field(default_factory=dict)
    prefix_lists: set[str] = Field(default_factory=set)
    access_lists: set[str] = Field(default_factory=set)


def parse_device_model(name: str, config_text: str) -> DeviceModel:
    """Parse raw Cisco IOS-XE configuration into a structured DeviceModel."""
    sha = hashlib.sha256(config_text.encode("utf-8")).hexdigest()

    # 1. Defined prefix-lists
    prefix_lists = set(
        re.findall(
            r"^ip\s+prefix-list\s+([a-zA-Z0-9_\-]+)\b",
            config_text,
            re.IGNORECASE | re.MULTILINE,
        )
    )

    # 2. Defined access-lists
    acl_named = set(
        re.findall(
            r"^ip\s+access-list\s+(?:standard|extended)\s+([a-zA-Z0-9_\-]+)\b",
            config_text,
            re.IGNORECASE | re.MULTILINE,
        )
    )
    acl_numbered = set(
        re.findall(
            r"^access-list\s+(\d+)\b",
            config_text,
            re.IGNORECASE | re.MULTILINE,
        )
    )
    access_lists = acl_named.union(acl_numbered)

    # 3. Route-maps
    route_maps: dict[str, list[RouteMapClauseModel]] = {}
    rm_headers = list(
        re.finditer(
            r"^route-map\s+([a-zA-Z0-9_\-]+)\s+(permit|deny)\s+(\d+)",
            config_text,
            re.IGNORECASE | re.MULTILINE,
        )
    )
    for i, match in enumerate(rm_headers):
        rm_name = match.group(1)
        action: Literal["permit", "deny"] = (
            "permit" if match.group(2).lower() == "permit" else "deny"
        )
        seq = int(match.group(3))

        start_pos = match.end()
        end_pos = rm_headers[i + 1].start() if i + 1 < len(rm_headers) else len(config_text)
        block = config_text[start_pos:end_pos]

        match_tags: list[int] = []
        set_tag: int | None = None
        match_pls: list[str] = []
        match_acls: list[str] = []
        match_intfs: list[str] = []
        set_metric: str | None = None
        raw_lines: list[str] = []

        for line in block.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith("!"):
                continue
            # End of route-map clause if unindented non-comment line starts
            if line and not line.startswith(" ") and not line.startswith("\t"):
                break
            raw_lines.append(line_str)

            # Match tag
            m_tag = re.search(r"match\s+tag\s+([0-9\s]+)", line_str, re.IGNORECASE)
            if m_tag:
                for t in m_tag.group(1).split():
                    if t.isdigit():
                        match_tags.append(int(t))

            # Set tag
            s_tag = re.search(r"set\s+tag\s+(\d+)", line_str, re.IGNORECASE)
            if s_tag:
                set_tag = int(s_tag.group(1))

            # Match prefix-list
            m_pl = re.search(
                r"match\s+ip\s+address\s+prefix-list\s+([a-zA-Z0-9_\-\s]+)",
                line_str,
                re.IGNORECASE,
            )
            if m_pl:
                for pl in m_pl.group(1).split():
                    match_pls.append(pl.strip())

            # Match ACL
            m_acl = re.search(
                r"match\s+ip\s+address\s+(?!prefix-list)([a-zA-Z0-9_\-]+)",
                line_str,
                re.IGNORECASE,
            )
            if m_acl:
                match_acls.append(m_acl.group(1).strip())

            # Match interface
            m_intf = re.search(r"match\s+interface\s+([a-zA-Z0-9_\-\/]+)", line_str, re.IGNORECASE)
            if m_intf:
                match_intfs.append(m_intf.group(1).strip())

            # Set metric
            m_sm = re.search(r"set\s+metric\s+([^\r\n]+)", line_str, re.IGNORECASE)
            if m_sm:
                set_metric = m_sm.group(1).strip()

        clause = RouteMapClauseModel(
            name=rm_name,
            action=action,
            sequence=seq,
            match_tags=match_tags,
            set_tag=set_tag,
            match_prefix_lists=match_pls,
            match_acls=match_acls,
            match_interfaces=match_intfs,
            set_metric=set_metric,
            raw_lines=raw_lines,
        )
        route_maps.setdefault(rm_name, []).append(clause)

    # 4. Routing processes (router eigrp <AS>, router ospf <ID>)
    processes: list[RoutingProcess] = []
    proc_headers = list(
        re.finditer(
            r"^router\s+(eigrp|ospf|bgp)\s+([a-zA-Z0-9_\-]+)",
            config_text,
            re.IGNORECASE | re.MULTILINE,
        )
    )

    for i, match in enumerate(proc_headers):
        proto = match.group(1).lower()
        proc_id = match.group(2)

        start_pos = match.end()
        end_pos = proc_headers[i + 1].start() if i + 1 < len(proc_headers) else len(config_text)
        block = config_text[start_pos:end_pos]

        router_id: str | None = None
        networks: list[str] = []
        redists: list[Redistribution] = []
        default_metric: str | None = None
        ospf_dist: int | None = None

        for line in block.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith("!"):
                continue
            if line and not line.startswith(" ") and not line.startswith("\t"):
                break

            # router-id
            m_rid = re.search(r"router-id\s+([0-9\.]+)", line_str, re.IGNORECASE)
            if m_rid:
                router_id = m_rid.group(1)

            # network
            m_net = re.search(r"network\s+([^\r\n]+)", line_str, re.IGNORECASE)
            if m_net:
                networks.append(m_net.group(1).strip())

            # default-metric
            m_dm = re.search(r"default-metric\s+([^\r\n]+)", line_str, re.IGNORECASE)
            if m_dm:
                default_metric = m_dm.group(1).strip()

            # distance ospf external <VAL>
            m_dist = re.search(
                r"distance\s+ospf\s+external\s+(\d+)",
                line_str,
                re.IGNORECASE,
            )
            if m_dist:
                ospf_dist = int(m_dist.group(1))

            # redistribute <proto> [<id>] [metric ...] [subnets] [metric-type ...] [route-map ...]
            if line_str.lower().startswith("redistribute"):
                r_parsed = _parse_redistribute_line(line_str)
                if r_parsed:
                    redists.append(r_parsed)

        processes.append(
            RoutingProcess(
                protocol=proto,
                process_id=proc_id,
                router_id=router_id,
                networks=networks,
                redistributions=redists,
                default_metric=default_metric,
                ospf_distance_external=ospf_dist,
            )
        )

    return DeviceModel(
        name=name,
        raw_config=config_text,
        config_sha256=sha,
        routing_processes=processes,
        route_maps=route_maps,
        prefix_lists=prefix_lists,
        access_lists=access_lists,
    )


def _parse_redistribute_line(line: str) -> Redistribution | None:
    """Parse a single 'redistribute ...' configuration statement."""
    # redistribute <source_protocol> [<source_id>] ...
    tokens = line.split()
    if len(tokens) < 2:
        return None

    src_proto = tokens[1].lower()
    idx = 2
    src_id: str | None = None
    if idx < len(tokens) and tokens[idx].lower() not in (
        "metric",
        "subnets",
        "metric-type",
        "route-map",
    ):
        src_id = tokens[idx]
        idx += 1

    subnets = bool(re.search(r"\bsubnets\b", line, re.IGNORECASE))

    # route-map
    rm_match = re.search(r"\broute-map\s+([a-zA-Z0-9_\-]+)", line, re.IGNORECASE)
    route_map = rm_match.group(1) if rm_match else None

    # metric-type
    mt_match = re.search(r"\bmetric-type\s+([12])\b", line, re.IGNORECASE)
    metric_type = mt_match.group(1) if mt_match else None

    # metric <values>
    metric: str | None = None
    m_match = re.search(
        r"\bmetric\s+((?:[0-9]+(?:\s+|$)){1,5})",
        line,
        re.IGNORECASE,
    )
    if m_match:
        metric = m_match.group(1).strip()

    return Redistribution(
        source_protocol=src_proto,
        source_id=src_id,
        metric=metric,
        subnets=subnets,
        metric_type=metric_type,
        route_map=route_map,
    )
