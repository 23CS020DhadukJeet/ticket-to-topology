"""Audit rules A1-A7 detecting redistribution risks and configuration defects."""

from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel

from t2t.audit.model import DeviceModel


class Finding(BaseModel):
    """Audit finding representing an identified configuration defect or risk."""

    rule_id: str
    severity: Literal["High", "Medium", "Low"]
    device: str
    message: str
    remediation: str
    exam_topic: str


AuditRule = Callable[[list[DeviceModel]], list[Finding]]


def rule_a1(models: list[DeviceModel]) -> list[Finding]:
    """A1: 'redistribute' without a route-map (device-level, High)."""
    findings: list[Finding] = []
    for m in models:
        for p in m.routing_processes:
            for r in p.redistributions:
                if not r.route_map:
                    findings.append(
                        Finding(
                            rule_id="A1",
                            severity="High",
                            device=m.name,
                            message=(
                                f"{m.name}: Process {p.protocol} {p.process_id} redistributes "
                                f"{r.source_protocol} without a route-map filter."
                            ),
                            remediation=(
                                f"Attach a route-map to filter prefixes and set tags (e.g. "
                                f"'redistribute {r.source_protocol} ... route-map <NAME>')."
                            ),
                            exam_topic="CCNP Enterprise Redistribution Filtering (Route-Maps)",
                        )
                    )
    return findings


def rule_a2(models: list[DeviceModel]) -> list[Finding]:
    """A2: redistribute into EIGRP with neither metric nor default-metric (device-level, High)."""
    findings: list[Finding] = []
    for m in models:
        for p in m.routing_processes:
            if p.protocol != "eigrp":
                continue
            for r in p.redistributions:
                # In EIGRP, connected and static routes derive metric from interface
                if r.source_protocol in ("connected", "static"):
                    continue
                if not r.metric and not p.default_metric:
                    findings.append(
                        Finding(
                            rule_id="A2",
                            severity="High",
                            device=m.name,
                            message=(
                                f"{m.name}: EIGRP {p.process_id} redistributes {r.source_protocol} "
                                f"with neither metric nor default-metric configured."
                            ),
                            remediation=(
                                "Specify metric parameters on the redistribute statement "
                                "('metric <bw> <delay> <rel> <load> <mtu>') or configure "
                                "'default-metric' under router eigrp."
                            ),
                            exam_topic="EIGRP Metric Calculation and Redistribution Requirements",
                        )
                    )
    return findings


def rule_a3(models: list[DeviceModel]) -> list[Finding]:
    """A3: redistribute into OSPF without 'subnets' (device-level, Medium)."""
    findings: list[Finding] = []
    for m in models:
        for p in m.routing_processes:
            if p.protocol != "ospf":
                continue
            for r in p.redistributions:
                if not r.subnets:
                    findings.append(
                        Finding(
                            rule_id="A3",
                            severity="Medium",
                            device=m.name,
                            message=(
                                f"{m.name}: OSPF {p.process_id} redistributes {r.source_protocol} "
                                "without 'subnets' keyword; subnetted prefixes will be dropped."
                            ),
                            remediation=(
                                f"Add 'subnets' to the redistribute command (e.g. "
                                f"'redistribute {r.source_protocol} subnets ...')."
                            ),
                            exam_topic="OSPF Subnets Redistribution",
                        )
                    )
    return findings


def _find_mutual_asbrs(
    models: list[DeviceModel],
) -> list[tuple[DeviceModel, str, str]]:
    """Identify devices performing two-way mutual redistribution between two protocols.

    Returns: list of (model, proto_a, proto_b)
    """
    asbrs: list[tuple[DeviceModel, str, str]] = []
    for m in models:
        proto_names = {p.protocol for p in m.routing_processes}
        if len(proto_names) < 2:
            continue

        for p1 in m.routing_processes:
            for p2 in m.routing_processes:
                if p1.protocol >= p2.protocol:
                    continue
                # Check if p1 redistributes p2 and p2 redistributes p1
                p1_redists_p2 = any(r.source_protocol == p2.protocol for r in p1.redistributions)
                p2_redists_p1 = any(r.source_protocol == p1.protocol for r in p2.redistributions)
                if p1_redists_p2 and p2_redists_p1:
                    asbrs.append((m, p1.protocol, p2.protocol))
    return asbrs


def rule_a4(models: list[DeviceModel]) -> list[Finding]:
    """A4: >= 2 ASBRs redistribute mutually without complete tag loop guard (High)."""
    asbr_list = _find_mutual_asbrs(models)
    if len(asbr_list) < 2:
        return []

    # Group by protocol pair (e.g. ("eigrp", "ospf"))
    pair_map: dict[tuple[str, str], list[DeviceModel]] = {}
    for m, p1, p2 in asbr_list:
        pair_map.setdefault((p1, p2), []).append(m)

    findings: list[Finding] = []

    for (p1, p2), asbr_devs in pair_map.items():
        if len(asbr_devs) < 2:
            continue

        # For direction p1 -> p2 (e.g. EIGRP into OSPF):
        # Collect all tags set by ANY ASBR when redistributing p1 into p2
        tags_set_p1_into_p2: set[int] = set()
        # And when redistributing p2 into p1:
        tags_set_p2_into_p1: set[int] = set()

        for m in asbr_devs:
            for p in m.routing_processes:
                if p.protocol == p2:
                    for r in p.redistributions:
                        if r.source_protocol == p1 and r.route_map:
                            clauses = m.route_maps.get(r.route_map, [])
                            for c in clauses:
                                if c.set_tag is not None:
                                    tags_set_p1_into_p2.add(c.set_tag)
                elif p.protocol == p1:
                    for r in p.redistributions:
                        if r.source_protocol == p2 and r.route_map:
                            clauses = m.route_maps.get(r.route_map, [])
                            for c in clauses:
                                if c.set_tag is not None:
                                    tags_set_p2_into_p1.add(c.set_tag)

        # Loop guard verification:
        # If no tags are set in either direction, guard is missing
        if not tags_set_p1_into_p2 or not tags_set_p2_into_p1:
            dev_str = ", ".join(d.name for d in asbr_devs)
            findings.append(
                Finding(
                    rule_id="A4",
                    severity="High",
                    device=dev_str,
                    message=(
                        f"Mutual redistribution ({p1} <-> {p2}) across ASBRs {dev_str} "
                        "does not set route tags in both directions for loop prevention."
                    ),
                    remediation=(
                        "Configure route-maps on all ASBRs to set a unique tag on "
                        "redistributed routes and deny routes with that tag in reverse direction."
                    ),
                    exam_topic="Multi-Point Two-Way Redistribution Loop Prevention (Route Tagging)",
                )
            )
            continue

        # Every tag set in p1 -> p2 must be denied in p2 -> p1 on EVERY ASBR
        # And every tag set in p2 -> p1 must be denied in p1 -> p2 on EVERY ASBR
        guard_complete = True
        missing_reasons: list[str] = []

        for m in asbr_devs:
            # Check p2 -> p1 route-map denies all tags_set_p1_into_p2
            denied_tags_in_p2_to_p1: set[int] = set()
            for p in m.routing_processes:
                if p.protocol == p1:
                    for r in p.redistributions:
                        if r.source_protocol == p2 and r.route_map:
                            clauses = m.route_maps.get(r.route_map, [])
                            for c in clauses:
                                if c.action == "deny":
                                    denied_tags_in_p2_to_p1.update(c.match_tags)

            if not tags_set_p1_into_p2.issubset(denied_tags_in_p2_to_p1):
                guard_complete = False
                missing = tags_set_p1_into_p2 - denied_tags_in_p2_to_p1
                missing_reasons.append(
                    f"{m.name} does not deny tag(s) {sorted(missing)} in {p2} -> {p1}"
                )

            # Check p1 -> p2 route-map denies all tags_set_p2_into_p1
            denied_tags_in_p1_to_p2: set[int] = set()
            for p in m.routing_processes:
                if p.protocol == p2:
                    for r in p.redistributions:
                        if r.source_protocol == p1 and r.route_map:
                            clauses = m.route_maps.get(r.route_map, [])
                            for c in clauses:
                                if c.action == "deny":
                                    denied_tags_in_p1_to_p2.update(c.match_tags)

            if not tags_set_p2_into_p1.issubset(denied_tags_in_p1_to_p2):
                guard_complete = False
                missing = tags_set_p2_into_p1 - denied_tags_in_p1_to_p2
                missing_reasons.append(
                    f"{m.name} does not deny tag(s) {sorted(missing)} in {p1} -> {p2}"
                )

        if not guard_complete:
            dev_str = ", ".join(d.name for d in asbr_devs)
            findings.append(
                Finding(
                    rule_id="A4",
                    severity="High",
                    device=dev_str,
                    message=(
                        f"Mutual redistribution ({p1} <-> {p2}) across ASBRs {dev_str} "
                        f"lacks a complete two-way tag loop guard: {'; '.join(missing_reasons)}."
                    ),
                    remediation=(
                        "Ensure every tag set in one direction is explicitly denied in a deny "
                        "clause in the reverse direction across all mutual ASBRs."
                    ),
                    exam_topic="Multi-Point Two-Way Redistribution Loop Prevention (Route Tagging)",
                )
            )

    return findings


def rule_a5(models: list[DeviceModel]) -> list[Finding]:
    """A5: ASBR mutual redistribution keeps default distance or differs (Medium)."""
    asbr_list = _find_mutual_asbrs(models)
    eigrp_ospf_asbrs = [m for m, p1, p2 in asbr_list if {p1, p2} == {"eigrp", "ospf"}]
    if not eigrp_ospf_asbrs:
        return []

    findings: list[Finding] = []
    asbr_distances: dict[str, int] = {}

    for m in eigrp_ospf_asbrs:
        ospf_proc = next((p for p in m.routing_processes if p.protocol == "ospf"), None)
        dist = (
            ospf_proc.ospf_distance_external
            if ospf_proc and ospf_proc.ospf_distance_external
            else 110
        )
        asbr_distances[m.name] = dist

    # Condition 1: Any ASBR leaves distance at default 110 (which is < EIGRP external 170)
    default_devs = [name for name, dist in asbr_distances.items() if dist == 110]

    # Condition 2: Distances differ across ASBRs
    distinct_dists = set(asbr_distances.values())
    differs = len(distinct_dists) > 1

    if default_devs or differs:
        dev_str = ", ".join(sorted(asbr_distances.keys()))
        dist_summary = ", ".join(f"{name}={dist}" for name, dist in sorted(asbr_distances.items()))
        findings.append(
            Finding(
                rule_id="A5",
                severity="Medium",
                device=dev_str,
                message=(
                    f"EIGRP <-> OSPF mutual ASBRs ({dev_str}) use default OSPF external distance "
                    f"or have differing distances ({dist_summary}), risking suboptimal routing."
                ),
                remediation=(
                    "Configure 'distance ospf external 171' under router ospf on all mutual ASBRs "
                    "so OSPF external routes do not preempt EIGRP external routes (AD 170)."
                ),
                exam_topic="Administrative Distance in Multi-Point Mutual Redistribution",
            )
        )

    return findings


def rule_a6(models: list[DeviceModel]) -> list[Finding]:
    """A6: route-map has no permit clause or references undefined filter (Medium)."""
    findings: list[Finding] = []

    for m in models:
        for p in m.routing_processes:
            for r in p.redistributions:
                if not r.route_map:
                    continue

                rm_name = r.route_map
                clauses = m.route_maps.get(rm_name)

                # Missing route-map definition entirely
                if clauses is None:
                    findings.append(
                        Finding(
                            rule_id="A6",
                            severity="Medium",
                            device=m.name,
                            message=f"{m.name}: Route-map '{rm_name}' is not defined.",
                            remediation=(f"Define route-map '{rm_name}' with permit/deny clauses."),
                            exam_topic="Route-Map Construction and Prefix-List Validation",
                        )
                    )
                    continue

                # No permit clause (only denies -> implicit deny drops everything, e.g. T6)
                has_permit = any(c.action == "permit" for c in clauses)
                if not has_permit:
                    findings.append(
                        Finding(
                            rule_id="A6",
                            severity="Medium",
                            device=m.name,
                            message=(
                                f"{m.name}: Route-map '{rm_name}' in {p.protocol} {p.process_id} "
                                "contains no permit clauses; all prefixes will be filtered."
                            ),
                            remediation=f"Add at least one permit clause to route-map '{rm_name}'.",
                            exam_topic="Route-Map Construction and Prefix-List Validation",
                        )
                    )

                # References to missing prefix-lists or ACLs
                for c in clauses:
                    for pl in c.match_prefix_lists:
                        if pl not in m.prefix_lists:
                            findings.append(
                                Finding(
                                    rule_id="A6",
                                    severity="Medium",
                                    device=m.name,
                                    message=(
                                        f"{m.name}: Route-map '{rm_name}' clause {c.sequence} "
                                        f"references undefined prefix-list '{pl}'."
                                    ),
                                    remediation=(
                                        f"Define 'ip prefix-list {pl}' or correct match clause."
                                    ),
                                    exam_topic="Route-Map Construction and Prefix-List Validation",
                                )
                            )
                    for acl in c.match_acls:
                        if acl not in m.access_lists:
                            findings.append(
                                Finding(
                                    rule_id="A6",
                                    severity="Medium",
                                    device=m.name,
                                    message=(
                                        f"{m.name}: Route-map '{rm_name}' clause {c.sequence} "
                                        f"references undefined access-list '{acl}'."
                                    ),
                                    remediation=(
                                        f"Define access-list '{acl}' or update match clause."
                                    ),
                                    exam_topic="Route-Map Construction and Prefix-List Validation",
                                )
                            )

    return findings


def rule_a7(models: list[DeviceModel]) -> list[Finding]:
    """A7 (stretch): metric-type differs between ASBRs (finds T8) (network-level, Medium)."""
    proto_asbrs: dict[str, dict[str, str]] = {}
    for m in models:
        for p in m.routing_processes:
            if p.protocol != "ospf":
                continue
            for r in p.redistributions:
                mt = r.metric_type or "2"  # Cisco default OSPF external metric-type is 2
                proto_asbrs.setdefault(r.source_protocol, {})[m.name] = mt

    findings: list[Finding] = []
    for src_proto, asbr_metric_types in proto_asbrs.items():
        if len(asbr_metric_types) < 2:
            continue
        distinct_types = set(asbr_metric_types.values())
        if len(distinct_types) > 1:
            dev_str = ", ".join(sorted(asbr_metric_types.keys()))
            type_summary = ", ".join(f"{k}=E{v}" for k, v in sorted(asbr_metric_types.items()))
            findings.append(
                Finding(
                    rule_id="A7",
                    severity="Medium",
                    device=dev_str,
                    message=(
                        f"OSPF external metric-type differs between ASBRs ({dev_str}) "
                        f"when redistributing {src_proto}: {type_summary}, "
                        "leading to asymmetric or suboptimal path selection."
                    ),
                    remediation=(
                        "Standardize metric-type (E1 or E2) on redistribute commands across ASBRs."
                    ),
                    exam_topic="OSPF External Metric Types (E1 vs E2)",
                )
            )
    return findings


ALL_RULES: list[AuditRule] = [
    rule_a1,
    rule_a2,
    rule_a3,
    rule_a4,
    rule_a5,
    rule_a6,
    rule_a7,
]


def run_audit(
    models: list[DeviceModel],
    rules: list[AuditRule] | None = None,
) -> list[Finding]:
    """Execute all or specified audit rules against the device models.

    Findings are sorted by severity: High -> Medium -> Low.
    """
    active_rules = rules if rules is not None else ALL_RULES
    findings: list[Finding] = []

    for rule_fn in active_rules:
        res = rule_fn(models)
        findings.extend(res)

    severity_order = {"High": 0, "Medium": 1, "Low": 2}
    findings.sort(key=lambda f: (severity_order.get(f.severity, 99), f.rule_id, f.device))
    return findings
