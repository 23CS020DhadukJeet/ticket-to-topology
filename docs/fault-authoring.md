# Fault Authoring Guide

All troubleshooting scenarios in `t2t` are defined declaratively as YAML files in `src/t2t/faults/catalog/`. Hard-coding faults in Python code is strictly prohibited by `AGENTS.md`.

---

## 1. Fault Schema Specification

Every fault file (e.g. `T3.yaml`) must conform to the `FaultModel` schema:

```yaml
id: "T3"
title: "OSPF distance override missing on R3"
level: 2                                     # 1 (easiest) to 5 (hardest)
symptom_class: "suboptimal"                  # outage | redundancy | suboptimal | latent
objectives:
  - "administrative-distance"

inject:
  R3:
    - "router ospf 1"
    - "no distance ospf external 171"

revert:
  R3:
    - "router ospf 1"
    - "distance ospf external 171"

flows:
  - src: "172.16.10.10"
    dst: "10.10.99.1"
    note: "HQ to vendor subnet traffic"

business_context: >
  Traffic from HQ to the vendor subnet is taking a suboptimal path across the WAN.

root_cause: >
  R3 lost its OSPF external distance override, causing OSPF AD 110 to beat EIGRP external AD 170.

key_concepts:
  - "administrative-distance"
  - "mutual-redistribution"

checks:
  - id: "c_t3_r3_route"
    kind: "route"
    router: "R3"
    params:
      prefix: "10.10.99.0/24"
      protocol: "eigrp"
      distance: 170

hints:
  1: "Look at how the two core routers pick between two sources for the vendor prefix."
  2: "Compare the administrative distance for external routes on R2 vs R3."
  3: "Configure 'distance ospf external 171' under router ospf 1 on R3."
```

---

## 2. Invariant Rules for Faults

1. **Counterpart Rule:** Every router modified in `inject` must have matching reversal configuration in `revert`.
2. **Three-Tier Hints:** Exactly 3 hints (keys 1, 2, 3) representing conceptual clue, localization clue, and exact CLI syntax.
3. **Verification Checks:** Must include at least one concrete check (`route`, `ping`, `neighbor`) that fails when the fault is injected and passes when reverted.
4. **Qualification:** Before inclusion in the catalog, faults must be qualified:
   ```bash
   t2t qualify --fault T3 --runs 3
   ```
