# Ticket-to-Topology (`t2t`)

**Ticket-to-Topology** is a dual-mode troubleshooting simulator and production configuration audit engine designed for multi-protocol mutual route redistribution (EIGRP $\leftrightarrow$ OSPF) on Cisco IOS-XE enterprise networks.

---

## Key Highlights

- **Dual Mode Operation:**
  - **Troubleshooting Simulator:** Injects realistic redistribution faults (suboptimal routing, micro-loops, blackholes), presents business-oriented incident tickets, provides pedagogical hint progression, evaluates candidate configuration fixes, and computes deterministic scores.
  - **Static & Live Network Audit Engine:** Inspects running configs or offline directory dumps against 7 industry-standard redistribution rules (A1–A7) to detect routing loops, missing subnet flags, and distance inconsistencies before they cause outages.
- **Strict Hardening & Zero-Drift Verification:**
  - Deterministic evaluation engine: PASS or FAIL is strictly determined by real network state checks (routes, ping reachability, OSPF/EIGRP neighbors).
  - Config drift detector: compares golden configuration sections against candidate modifications using unified diffing to guarantee minimal, surgically clean remediation.
- **Offline Replay Mode (`--replay`):**
  - Run and qualify tickets, check commands, and full audit scans completely offline against frozen fixtures without live router hardware or network connectivity.

---

## Core Topologies & Architecture

The simulator models a classic dual-homed enterprise topology:
- **R1 (Branch):** EIGRP AS 100 leaf router.
- **R2 (ASBR 1):** Dual-protocol boundary router performing mutual EIGRP 100 $\leftrightarrow$ OSPF 1 redistribution with route-maps, tag loop guards, and distance overrides.
- **R3 (ASBR 2):** Redundant dual-protocol boundary router mirroring redistribution policies.
- **R4 (HQ / Core):** OSPF Area 0 core router.
