# Cisco IOS-XE Redistribution Audit Rules Reference

This document details the redistribution audit rules (A1–A7) implemented by `t2t audit`. These rules detect critical configuration risks, race conditions, routing feedback loops, and suboptimal routing in multi-protocol Cisco IOS-XE enterprise networks.

---

## Summary Matrix

| Rule ID | Severity | Scope | Finding Summary | Exam Topic |
|---|---|---|---|---|
| **A1** | **High** | Device | `redistribute` without a route-map | Redistribution Filtering (Route-Maps) |
| **A2** | **High** | Device | Redistribute into EIGRP without metric or `default-metric` | EIGRP Seed Metric Calculation |
| **A3** | **Medium** | Device | Redistribute into OSPF without `subnets` | OSPF Subnets Redistribution |
| **A4** | **High** | Network | Multi-ASBR mutual redistribution lacks two-way tag loop guard | Multi-Point Two-Way Loop Prevention |
| **A5** | **Medium** | Network | EIGRP $\leftrightarrow$ OSPF mutual ASBRs use default OSPF distance or differ | Administrative Distance in Mutual Redistribution |
| **A6** | **Medium** | Device | Route-map has no permit clause or references undefined prefix-list/ACL | Route-Map Construction & Validation |
| **A7** | **Medium** | Network | External OSPF metric-type differs between ASBRs (E1 vs E2) | OSPF External Metrics (E1 vs E2) |

---

## Rule A1: Redistribution Without Route-Map Filter

- **Severity:** High
- **Scope:** Device-level
- **Exam Topic:** CCNP Enterprise ENCOR / ENARSI — Redistribution Filtering & Tagging

### Risk & Network Impact
Redistributing one routing protocol directly into another without an attached route-map injects every route known by the source protocol into the target protocol with default attributes. In multi-homed or multi-ASBR topologies, unconstrained redistribution causes routing feedback loops, route flapping, blackholing, and domain poisoning.

### Non-Compliant Configuration
```cisco
router ospf 1
 router-id 2.2.2.2
 network 10.1.24.0 0.0.0.255 area 0
 redistribute eigrp 100 subnets
```

### Remediated Configuration
Attach a route-map to filter desired prefixes and tag injected routes:
```cisco
ip prefix-list PERMIT-BRANCH-NETS seq 10 permit 10.10.1.0/24
ip prefix-list PERMIT-BRANCH-NETS seq 20 permit 10.10.2.0/24
!
route-map EIGRP-TO-OSPF deny 10
 match tag 200
!
route-map EIGRP-TO-OSPF permit 20
 match ip address prefix-list PERMIT-BRANCH-NETS
 set tag 100
!
router ospf 1
 redistribute eigrp 100 subnets route-map EIGRP-TO-OSPF
```

---

## Rule A2: EIGRP Redistribution Without Seed Metric

- **Severity:** High
- **Scope:** Device-level
- **Exam Topic:** CCNP Enterprise ENARSI — EIGRP Seed Metric Requirements

### Risk & Network Impact
Unlike OSPF (which defaults to a seed metric of 20 for non-BGP routes), EIGRP considers routes redistributed from other routing protocols (OSPF, BGP, RIP) to have an **infinite composite metric** unless explicitly configured. Routes with infinite metric are dropped at ingestion and never entered into the EIGRP topology table, resulting in complete failure to redistribute routes.

*(Note: Directly connected and static routes derive metric parameters from interface characteristics and are exempt from this requirement).*

### Non-Compliant Configuration
```cisco
router eigrp 100
 network 10.1.12.0 0.0.0.255
 redistribute ospf 1 route-map OSPF-TO-EIGRP
```

### Remediated Configuration
Configure metric parameters (`bandwidth delay reliability load mtu`) on the `redistribute` command or define a `default-metric` under the EIGRP process:
```cisco
router eigrp 100
 network 10.1.12.0 0.0.0.255
 default-metric 10000 100 255 1 1500
 redistribute ospf 1 route-map OSPF-TO-EIGRP
! Or alternatively:
router eigrp 100
 redistribute ospf 1 metric 10000 100 255 1 1500 route-map OSPF-TO-EIGRP
```

---

## Rule A3: OSPF Redistribution Without Subnets Keyword

- **Severity:** Medium
- **Scope:** Device-level
- **Exam Topic:** CCNP Enterprise ENCOR — OSPF Route Redistribution

### Risk & Network Impact
In Cisco IOS-XE, the default behavior of `redistribute ...` under `router ospf` is classful: only natural major network boundaries (/8, /16, /24) are redistributed. Any subnetted or VLSM prefixes (e.g., /25, /28, /30) are silently dropped. In modern networks, virtually all IP networks are subnetted; omitting `subnets` results in partial or complete loss of reachability.

### Non-Compliant Configuration
```cisco
router ospf 1
 router-id 2.2.2.2
 redistribute eigrp 100 route-map EIGRP-TO-OSPF
```

### Remediated Configuration
Include the `subnets` keyword on the redistribute statement:
```cisco
router ospf 1
 router-id 2.2.2.2
 redistribute eigrp 100 subnets route-map EIGRP-TO-OSPF
```

---

## Rule A4: Missing Two-Way Tag Loop Guard on Multi-Point ASBRs

- **Severity:** High
- **Scope:** Network-level (cross-device comparison)
- **Exam Topic:** CCNP Enterprise ENARSI — Multi-Point Mutual Redistribution Loop Prevention

### Risk & Network Impact
When two or more ASBRs perform mutual two-way redistribution between two routing domains (e.g., EIGRP and OSPF), routes redistributed by ASBR1 into OSPF can be learned by ASBR2 and redistributed back into EIGRP. This route feedback causes permanent routing loops, routing table instability, and suboptimal forwarding.

To prevent loops, **every tag set in one direction must be denied in the reverse direction across all mutual ASBRs**.

### Non-Compliant Configuration
- **R2 sets tag 100 into OSPF; denies tag 200.**
- **R3 sets tag 100 into OSPF, but forgets to deny tag 200 before permitting:**
```cisco
! On R3:
route-map OSPF-TO-EIGRP permit 10
 set tag 200
! Missing: route-map OSPF-TO-EIGRP deny 10 match tag 100
```

### Remediated Configuration
Implement reciprocal tag filtering across all mutual ASBRs (R2 and R3):
```cisco
! On both R2 and R3:
! EIGRP -> OSPF: Deny routes tagged 200 (originated in OSPF), permit and tag 100
route-map EIGRP-TO-OSPF deny 10
 match tag 200
route-map EIGRP-TO-OSPF permit 20
 set tag 100
!
! OSPF -> EIGRP: Deny routes tagged 100 (originated in EIGRP), permit and tag 200
route-map OSPF-TO-EIGRP deny 10
 match tag 100
route-map OSPF-TO-EIGRP permit 20
 match ip address prefix-list HQ-NETS
 set tag 200
```

---

## Rule A5: Default or Inconsistent OSPF External Administrative Distance

- **Severity:** Medium
- **Scope:** Network-level (cross-device comparison)
- **Exam Topic:** CCNP Enterprise ENARSI — Administrative Distance Tuning

### Risk & Network Impact
- EIGRP internal AD = **90**, external AD = **170**.
- OSPF intra/inter-area AD = **110**, external (E1/E2) AD = **110**.

When ASBR1 redistributes an EIGRP route into OSPF, it enters OSPF with AD 110. When ASBR2 receives this route via OSPF, its AD (110) is lower than the native EIGRP external AD (170). Consequently, ASBR2 installs the route via OSPF rather than EIGRP, leading to suboptimal routing and race-condition feedback.

### Non-Compliant Configuration
ASBRs leave OSPF external distance at the default of 110:
```cisco
router ospf 1
 router-id 2.2.2.2
 redistribute eigrp 100 subnets route-map EIGRP-TO-OSPF
 ! distance ospf external command omitted
```

### Remediated Configuration
Set `distance ospf external 171` (higher than EIGRP external 170) on all mutual ASBRs:
```cisco
router ospf 1
 router-id 2.2.2.2
 distance ospf external 171
```

---

## Rule A6: Route-Map Permit Missing or Undefined Prefix-List / ACL

- **Severity:** Medium
- **Scope:** Device-level
- **Exam Topic:** CCNP Enterprise ENCOR — Route-Map Logic and Prefix Matching

### Risk & Network Impact
1. **No permit clause:** A route-map consisting exclusively of `deny` clauses will drop all candidate prefixes due to the implicit `deny 65535` at the end of every route-map, resulting in zero redistributed routes.
2. **Missing prefix-list or ACL:** If a route-map clause references a prefix-list or ACL that is not defined in the configuration, Cisco IOS-XE treats the match condition as matching nothing (or false), causing prefixes to fall through to subsequent clauses or get dropped.

### Non-Compliant Configuration
```cisco
route-map OSPF-TO-EIGRP deny 10
 match tag 100
route-map OSPF-TO-EIGRP deny 20
 match tag 200
! (No permit clause exists; all routes will be filtered!)
```
Or:
```cisco
route-map OSPF-TO-EIGRP permit 20
 match ip address prefix-list NONEXISTENT-PL
! (NONEXISTENT-PL is not defined anywhere in the running-config!)
```

### Remediated Configuration
Ensure at least one permit clause exists and all referenced filters are explicitly defined:
```cisco
ip prefix-list HQ-NETS seq 10 permit 172.16.10.0/24
!
route-map OSPF-TO-EIGRP deny 10
 match tag 100
route-map OSPF-TO-EIGRP permit 20
 match ip address prefix-list HQ-NETS
 set tag 200
```

---

## Rule A7: OSPF External Metric-Type Mismatch Across ASBRs

- **Severity:** Medium
- **Scope:** Network-level
- **Exam Topic:** CCNP Enterprise ENARSI — OSPF Path Selection (E1 vs E2)

### Risk & Network Impact
OSPF supports two external metric types:
- **E1 (Type 1):** Metric reflects external cost plus internal intra-area cost to the ASBR.
- **E2 (Type 2, Default):** Metric reflects only the external cost announced by the ASBR.

OSPF path selection rules state that **E1 routes always take precedence over E2 routes**, regardless of cost. If ASBR1 redistributes a prefix as E1 and ASBR2 redistributes as E2, internal routers (e.g. core router R4) will always route via ASBR1, breaking ECMP load-balancing and causing asymmetric forwarding.

### Non-Compliant Configuration
- **R2:**
  ```cisco
  router ospf 1
   redistribute eigrp 100 subnets metric-type 1 route-map EIGRP-TO-OSPF
  ```
- **R3:**
  ```cisco
  router ospf 1
   redistribute eigrp 100 subnets metric-type 2 route-map EIGRP-TO-OSPF
  ```

### Remediated Configuration
Standardize external metric types across all ASBRs:
```cisco
! On both R2 and R3:
router ospf 1
 redistribute eigrp 100 subnets route-map EIGRP-TO-OSPF
```
