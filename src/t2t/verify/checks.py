"""Check kind parameter models and implementation functions.

NOTE: Per AGENTS.md Hard Rule 3, t2t.verify must never import t2t.ai.
"""

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from t2t.clock import Clock
from t2t.models import Check, CheckResult
from t2t.parsers.neighbors import parse_eigrp_neighbors, parse_ospf_neighbors
from t2t.parsers.route import parse_route_detail
from t2t.parsers.routemap import parse_route_maps


class RoutePresentParams(BaseModel):
    """Parameters for 'route_present' check."""

    protocol: str | None = None
    distance: int | None = None
    tag: int | None = None
    min_paths: int | None = None
    next_hops_include: list[str] | None = None


class RouteAbsentParams(BaseModel):
    """Parameters for 'route_absent' check."""


class RouteNextHopsParams(BaseModel):
    """Parameters for 'route_next_hops' check."""

    must_include: list[str] = Field(default_factory=list)
    must_exclude: list[str] = Field(default_factory=list)


class NeighborUpParams(BaseModel):
    """Parameters for 'neighbor_up' check."""

    protocol: Literal["eigrp", "ospf"]
    address: str


class ConfigContainsParams(BaseModel):
    """Parameters for 'config_contains' check."""

    section: str
    regex: str


class ConfigAbsentParams(BaseModel):
    """Parameters for 'config_absent' check."""

    section: str
    regex: str


class RouteMapClauseParams(BaseModel):
    """Parameters for 'routemap_clause' check."""

    name: str
    seq: int
    action: Literal["permit", "deny"]
    match: dict[str, str] | None = None
    set: dict[str, str] | None = None


class PingParams(BaseModel):
    """Parameters for 'ping' check."""

    source: str
    dest: str
    min_success_pct: int = 100


class StableParams(BaseModel):
    """Parameters for 'stable' check."""

    samples: int = 3
    interval_s: float = 1.0


CHECK_PARAM_MODELS: dict[str, type[BaseModel]] = {
    "route_present": RoutePresentParams,
    "route_absent": RouteAbsentParams,
    "route_next_hops": RouteNextHopsParams,
    "neighbor_up": NeighborUpParams,
    "config_contains": ConfigContainsParams,
    "config_absent": ConfigAbsentParams,
    "routemap_clause": RouteMapClauseParams,
    "ping": PingParams,
    "stable": StableParams,
}


def execute_route_present(check: Check, session: Any, clock: Clock) -> CheckResult:
    """Verify prefix is present in RIB with matching attributes."""
    params = RoutePresentParams.model_validate(check.params)
    prefix_str = check.prefix or ""
    out = session.show(check.router, f"show ip route {prefix_str}".strip())
    route = parse_route_detail(out)

    if route is None:
        return CheckResult(
            check_id=check.id,
            passed=False,
            expected=f"Prefix {prefix_str} present in RIB",
            observed="Prefix not in table",
            message=f"{check.router}: prefix {prefix_str} missing from routing table.",
        )

    # Check protocol
    if params.protocol and route.protocol.lower() != params.protocol.lower():
        msg = (
            f"{check.router}: prefix {prefix_str} known via {route.protocol}, "
            f"expected {params.protocol}."
        )
        return CheckResult(
            check_id=check.id,
            passed=False,
            expected=f"protocol={params.protocol}",
            observed=f"protocol={route.protocol}",
            message=msg,
        )

    # Check distance
    if params.distance is not None and route.distance != params.distance:
        msg = (
            f"{check.router}: prefix {prefix_str} AD is {route.distance}, "
            f"expected {params.distance}."
        )
        return CheckResult(
            check_id=check.id,
            passed=False,
            expected=f"distance={params.distance}",
            observed=f"distance={route.distance}",
            message=msg,
        )

    # Check tag
    if params.tag is not None and route.tag != params.tag:
        msg = f"{check.router}: prefix {prefix_str} tag is {route.tag}, expected {params.tag}."
        return CheckResult(
            check_id=check.id,
            passed=False,
            expected=f"tag={params.tag}",
            observed=f"tag={route.tag}",
            message=msg,
        )

    # Check min paths
    if params.min_paths is not None and len(route.next_hops) < params.min_paths:
        msg = (
            f"{check.router}: prefix {prefix_str} has {len(route.next_hops)} paths, "
            f"expected >= {params.min_paths}."
        )
        return CheckResult(
            check_id=check.id,
            passed=False,
            expected=f"min_paths={params.min_paths}",
            observed=f"paths={len(route.next_hops)}",
            message=msg,
        )

    # Check next_hops_include
    if params.next_hops_include:
        actual_hops = {hop.ip for hop in route.next_hops}
        missing_hops = set(params.next_hops_include) - actual_hops
        if missing_hops:
            msg = (
                f"{check.router}: prefix {prefix_str} missing expected next-hops: "
                f"{list(missing_hops)}."
            )
            return CheckResult(
                check_id=check.id,
                passed=False,
                expected=f"next_hops_include={params.next_hops_include}",
                observed=f"next_hops={list(actual_hops)}",
                message=msg,
            )

    obs = (
        f"Present (protocol={route.protocol}, distance={route.distance}, "
        f"hops={len(route.next_hops)})"
    )
    return CheckResult(
        check_id=check.id,
        passed=True,
        expected=f"Prefix {prefix_str} present with matching attributes",
        observed=obs,
        message=f"{check.router}: prefix {prefix_str} verified successfully.",
    )


def execute_route_absent(check: Check, session: Any, clock: Clock) -> CheckResult:
    """Verify prefix is not in RIB."""
    prefix_str = check.prefix or ""
    out = session.show(check.router, f"show ip route {prefix_str}".strip())
    route = parse_route_detail(out)

    if route is not None:
        return CheckResult(
            check_id=check.id,
            passed=False,
            expected=f"Prefix {prefix_str} absent from RIB",
            observed=f"Present via {route.protocol} (AD {route.distance})",
            message=f"{check.router}: prefix {prefix_str} is unexpectedly present in RIB.",
        )

    return CheckResult(
        check_id=check.id,
        passed=True,
        expected=f"Prefix {prefix_str} absent from RIB",
        observed="Not in table",
        message=f"{check.router}: prefix {prefix_str} is absent as expected.",
    )


def execute_route_next_hops(check: Check, session: Any, clock: Clock) -> CheckResult:
    """Verify route next hops against inclusion and exclusion constraints."""
    params = RouteNextHopsParams.model_validate(check.params)
    prefix_str = check.prefix or ""
    out = session.show(check.router, f"show ip route {prefix_str}".strip())
    route = parse_route_detail(out)

    if route is None:
        return CheckResult(
            check_id=check.id,
            passed=False,
            expected="Route present",
            observed="Not in table",
            message=f"{check.router}: cannot check next-hops, prefix {prefix_str} missing.",
        )

    actual_hops = {hop.ip for hop in route.next_hops}

    if params.must_include:
        missing = set(params.must_include) - actual_hops
        if missing:
            return CheckResult(
                check_id=check.id,
                passed=False,
                expected=f"must_include={params.must_include}",
                observed=f"actual={list(actual_hops)}",
                message=f"{check.router}: missing required next hops {list(missing)}.",
            )

    if params.must_exclude:
        forbidden = set(params.must_exclude) & actual_hops
        if forbidden:
            return CheckResult(
                check_id=check.id,
                passed=False,
                expected=f"must_exclude={params.must_exclude}",
                observed=f"actual={list(actual_hops)}",
                message=f"{check.router}: contains forbidden next hops {list(forbidden)}.",
            )

    return CheckResult(
        check_id=check.id,
        passed=True,
        expected="Next hops satisfied constraints",
        observed=f"Hops={list(actual_hops)}",
        message=f"{check.router}: next hops for {prefix_str} meet all constraints.",
    )


def execute_neighbor_up(check: Check, session: Any, clock: Clock) -> CheckResult:
    """Verify routing neighbor is established and up."""
    params = NeighborUpParams.model_validate(check.params)
    if params.protocol == "eigrp":
        out = session.show(check.router, "show ip eigrp neighbors")
        nbrs = parse_eigrp_neighbors(out)
        matching = [n for n in nbrs if n.address == params.address]
        is_up = len(matching) > 0
    else:  # ospf
        out = session.show(check.router, "show ip ospf neighbor")
        nbrs = parse_ospf_neighbors(out)
        matching = [n for n in nbrs if n.address == params.address]
        is_up = len(matching) > 0 and matching[0].state.startswith("FULL")

    proto_name = params.protocol.upper()
    if not is_up:
        return CheckResult(
            check_id=check.id,
            passed=False,
            expected=f"{proto_name} neighbor {params.address} UP",
            observed="DOWN or missing" if not matching else matching[0].state,
            message=f"{check.router}: {proto_name} neighbor {params.address} is not up.",
        )

    return CheckResult(
        check_id=check.id,
        passed=True,
        expected=f"{proto_name} neighbor {params.address} UP",
        observed="UP" if params.protocol == "eigrp" else matching[0].state,
        message=f"{check.router}: {proto_name} neighbor {params.address} is established.",
    )


def execute_config_contains(check: Check, session: Any, clock: Clock) -> CheckResult:
    """Verify regex matches inside running-config section."""
    params = ConfigContainsParams.model_validate(check.params)
    out = session.show(check.router, f"show running-config | section {params.section}")
    matched = re.search(params.regex, out, re.MULTILINE)

    if not matched:
        msg = f"{check.router}: config section '{params.section}' lacks '{params.regex}'."
        return CheckResult(
            check_id=check.id,
            passed=False,
            expected=f"Config section '{params.section}' matches '{params.regex}'",
            observed="No match in section",
            message=msg,
        )

    return CheckResult(
        check_id=check.id,
        passed=True,
        expected=f"Config section '{params.section}' matches '{params.regex}'",
        observed="Match found",
        message=f"{check.router}: section '{params.section}' contains expected config.",
    )


def execute_config_absent(check: Check, session: Any, clock: Clock) -> CheckResult:
    """Verify regex does not match inside running-config section."""
    params = ConfigAbsentParams.model_validate(check.params)
    out = session.show(check.router, f"show running-config | section {params.section}")
    matched = re.search(params.regex, out, re.MULTILINE)

    if matched:
        msg = f"{check.router}: section '{params.section}' contains forbidden '{params.regex}'."
        return CheckResult(
            check_id=check.id,
            passed=False,
            expected=f"Config section '{params.section}' does NOT match '{params.regex}'",
            observed=f"Match found: '{matched.group(0)}'",
            message=msg,
        )

    return CheckResult(
        check_id=check.id,
        passed=True,
        expected=f"Config section '{params.section}' does NOT match '{params.regex}'",
        observed="No match",
        message=f"{check.router}: forbidden config absent from section '{params.section}'.",
    )


def execute_routemap_clause(check: Check, session: Any, clock: Clock) -> CheckResult:
    """Verify a specific route-map clause exists with expected match/set properties."""
    params = RouteMapClauseParams.model_validate(check.params)
    out = session.show(check.router, f"show route-map {params.name}")
    clauses = parse_route_maps(out)

    matching = [
        c
        for c in clauses
        if c.name == params.name and c.seq == params.seq and c.action == params.action
    ]
    if not matching:
        msg = f"{check.router}: map {params.name} clause {params.seq} ({params.action}) missing."
        return CheckResult(
            check_id=check.id,
            passed=False,
            expected=f"route-map {params.name} {params.action} {params.seq}",
            observed="Clause not found",
            message=msg,
        )

    clause = matching[0]
    if params.match:
        for k, v in params.match.items():
            if clause.match.get(k.lower()) != v:
                msg = f"{check.router}: clause {clause.name} seq {clause.seq} match {k} mismatch."
                return CheckResult(
                    check_id=check.id,
                    passed=False,
                    expected=f"match {k} {v}",
                    observed=f"match {k} {clause.match.get(k.lower())}",
                    message=msg,
                )

    if params.set:
        for k, v in params.set.items():
            if clause.set.get(k.lower()) != v:
                msg = f"{check.router}: clause {clause.name} seq {clause.seq} set {k} mismatch."
                return CheckResult(
                    check_id=check.id,
                    passed=False,
                    expected=f"set {k} {v}",
                    observed=f"set {k} {clause.set.get(k.lower())}",
                    message=msg,
                )

    return CheckResult(
        check_id=check.id,
        passed=True,
        expected=f"route-map {params.name} {params.action} {params.seq} verified",
        observed="Clause matches expected criteria",
        message=f"{check.router}: route-map {params.name} clause {params.seq} verified.",
    )


def execute_ping(check: Check, session: Any, clock: Clock) -> CheckResult:
    """Verify ping reachability and success rate."""
    params = PingParams.model_validate(check.params)
    out = session.show(check.router, f"ping {params.dest} source {params.source}")
    pct_match = re.search(r"Success rate is\s+(\d+)\s+percent", out)
    success_pct = int(pct_match.group(1)) if pct_match else 0

    passed = success_pct >= params.min_success_pct
    msg = f"{check.router}: ping {params.source}->{params.dest} had {success_pct}% success."
    return CheckResult(
        check_id=check.id,
        passed=passed,
        expected=f"success_pct >= {params.min_success_pct}%",
        observed=f"success_pct = {success_pct}%",
        message=msg,
    )


def execute_stable(check: Check, session: Any, clock: Clock) -> CheckResult:
    """Verify prefix routing state does not flap across N samples."""
    params = StableParams.model_validate(check.params)
    prefix_str = check.prefix or ""

    samples: list[str] = []
    for i in range(params.samples):
        out = session.show(check.router, f"show ip route {prefix_str}".strip())
        route = parse_route_detail(out)
        state_repr = (
            "absent"
            if route is None
            else f"{route.protocol}:{route.distance}:{route.tag}:{[h.ip for h in route.next_hops]}"
        )
        samples.append(state_repr)
        if i < params.samples - 1:
            clock.sleep(params.interval_s)

    # Check that all samples are identical
    if len(set(samples)) > 1:
        msg = f"{check.router}: route for {prefix_str} is not stable (flipped across samples)."
        return CheckResult(
            check_id=check.id,
            passed=False,
            expected=f"Stable state across {params.samples} samples",
            observed=f"State flip detected: {samples}",
            message=msg,
        )

    return CheckResult(
        check_id=check.id,
        passed=True,
        expected=f"Stable state across {params.samples} samples",
        observed=f"Constant state: {samples[0]}",
        message=f"{check.router}: prefix {prefix_str} remained stable.",
    )


CHECK_DISPATCH: dict[str, Any] = {
    "route_present": execute_route_present,
    "route_absent": execute_route_absent,
    "route_next_hops": execute_route_next_hops,
    "neighbor_up": execute_neighbor_up,
    "config_contains": execute_config_contains,
    "config_absent": execute_config_absent,
    "routemap_clause": execute_routemap_clause,
    "ping": execute_ping,
    "stable": execute_stable,
}
