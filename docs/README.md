# Ticket-to-Topology (`t2t`): Master Project Reference Manual

> **A Dual-Mode Pedagogical & Automated Verification Platform for Multi-Point Mutual Route Redistribution, Route Feedback Elimination, and Cisco IOS-XE Configuration Auditing**

---

## 1. Academic & Professional Course Alignment

This project is engineered to bridge theoretical routing protocol mechanics with operational, verifiable software automation. It aligns with multiple professional and academic curricula:

| Curriculum / Credential | Domain / Module | Alignment in `t2t` |
| :--- | :--- | :--- |
| **Cisco CCNP Enterprise ENCOR (350-401)** | Section 3.0: Infrastructure (3.1 Routing protocols, 3.2 Redistribution, 3.3 Path selection) | Core 4-router dual-boundary topology; EIGRP AS 100 $\leftrightarrow$ OSPF Area 0 mutual redistribution; administrative distance tuning. |
| **Cisco CCNP Enterprise ENARSI (300-410)** | Section 1.0: Layer 3 Technologies (1.1 Troubleshoot administrative distance, 1.2 Troubleshoot route redistribution between any routing protocols) | Parameterized fault scenarios (T1–T7); static audit rules (A1–A7); route tagging; prefix filtering; loop detection. |
| **NPTEL / University Networking (B.Tech CSE)** | Advanced Computer Networks / Capstone Software Project | AST grammar parsing for Cisco IOS-XE; Finite State Machine session management; deterministic Verification Oracle; Socratic AI guidance. |

---

## 2. The Core Routing Challenge: Multi-Point Mutual Redistribution

In enterprise network architecture, interconnecting disparate Interior Gateway Protocols (IGPs) is common following mergers, acquisitions, or multi-vendor infrastructure rollouts. Bridging an **EIGRP** autonomous system with an **OSPF** link-state domain at multiple points (**dual ASBRs**) introduces critical control-plane vulnerabilities:

```
  +--------------------+                     +--------------------+
  |                    |--- Gig0/1 --- Gig0/1|                    |
  |     R1 (Branch)    |    (10.1.12.0/24)   |      R2 (ASBR)     |
  |   EIGRP AS 100     |                     |  EIGRP 100 <-> OSPF|--- Gig0/2 --- Gig0/1
  |  AD 90 (Internal)  |--- Gig0/2 --- Gig0/1|                    |    (10.1.24.0/24)   |
  +--------------------+    (10.1.13.0/24)   +--------------------+                     |   +---------------+
                                                        |                               |---|   R4 (HQ)     |
                                                   Gig0/3 - Gig0/3                      |   | OSPF Area 0   |
                                                    (10.1.23.0/24)                      |   | AD 110 (Flat) |
                                                        |                               |---| (10.10.99.0)  |
                                             +--------------------+                     |   +---------------+
                                             |                    |--- Gig0/2 --- Gig0/2
                                             |      R3 (ASBR)     |    (10.1.34.0/24)
                                             |  EIGRP 100 <-> OSPF|
                                             +--------------------+
```

### Why Naive Redistribution Fails

1. **Metric Incompatibility**: EIGRP uses composite vector metrics (bandwidth, delay, reliability, load, MTU). OSPF uses link cost based on inverse bandwidth. Neither translates automatically into the other without manual seed metrics (`default-metric` or `metric` argument in `redistribute`). Without explicit seeds, redistributed routes enter with metric 0 or infinity and get silently dropped.
2. **Administrative Distance (AD) Inversion**:
   * EIGRP Internal routes: $\text{AD} = 90$
   * OSPF intra-area, inter-area, and external routes: $\text{AD} = 110$
   * EIGRP External (redistributed) routes: $\text{AD} = 170$
   * **The Hazard**: When R2 redistributes an EIGRP route into OSPF, R3 learns that route via OSPF with $\text{AD} = 110$. R3 also knows the same prefix directly via EIGRP with external $\text{AD} = 170$. Because $110 < 170$, R3 installs the suboptimal OSPF path through R2 rather than the direct EIGRP path!
3. **Route Feedback Loops**: R3 re-advertises the prefix back into EIGRP with new metrics, causing traffic to bounce infinitely between R2 and R3 until TTL expiration.
4. **Remediation Techniques**:
   * **Route Tagging**: ASBRs stamp external routes with numerical tags (e.g., `set tag 110` when going into OSPF; `match tag 110` with `deny` when redistributing back into EIGRP).
   * **Administrative Distance Tuning**: Modifying OSPF external distance (`distance ospf external 171`) so that EIGRP external ($170 < 171$) is strictly preferred.
   * **Prefix-List Filtering**: Explicitly restricting permitted subnets per direction.

---

## 3. System Architecture & High-Level Design

Ticket-to-Topology solves these challenges through a loosely coupled, multi-tier software architecture:

```
+-----------------------------------------------------------------------------------+
|                           PRESENTATION LAYER                                      |
|   +------------------------------------+    +---------------------------------+   |
|   | Typer CLI (Rich Tables & Spinners) |    | FastAPI Read-Only Web Server    |   |
|   | t2t new-ticket | audit | submit    |    | GET /api/status | /api/session  |   |
|   +------------------------------------+    | Interactive SVG Dynamic Canvas  |   |
|                                             +---------------------------------+   |
+-----------------------------------------------------------------------------------+
                                         |
+-----------------------------------------------------------------------------------+
|                        APPLICATION & DOMAIN LAYER                                 |
|   +-----------------------+   +----------------------+   +--------------------+   |
|   | IOS-XE AST Parser     |   | Static Audit Engine  |   | Fault Injector     |   |
|   | Indentation Grammar   |   | Rules A1 - A7        |   | Catalog YAML T1-T7 |   |
|   +-----------------------+   +----------------------+   +--------------------+   |
|   +-----------------------+   +----------------------+   +--------------------+   |
|   | Verification Oracle   |   | Scoring & Anti-Drift |   | Socratic AI Mentor |   |
|   | Invariant Route Check |   | Time Decay + Levensh.|   | Regex Redaction    |   |
|   +-----------------------+   +----------------------+   +--------------------+   |
+-----------------------------------------------------------------------------------+
                                         |
+-----------------------------------------------------------------------------------+
|                       INFRASTRUCTURE & ADAPTER LAYER                             |
|   +------------------------------------+    +---------------------------------+   |
|   | DeviceSession (DeviceProtocol)     |    | SQLite 3 (WAL Mode Repository)  |   |
|   | - NetmikoDevice (Live SSH)         |    | - sessions, attempts, checks    |   |
|   | - MockDevice (Offline Replay Fixt) |    | - ACID transactions & FK checks |   |
|   +------------------------------------+    +---------------------------------+   |
+-----------------------------------------------------------------------------------+
```

### Key Architectural Pillars

* **Dual-Mode Operation**: Serves as both a **live interactive troubleshooting game** and a **production static audit engine** that evaluates configurations offline.
* **Deterministic Verification Oracle (Rule 3 in AGENTS.md)**: Pass/Fail decisions are computed purely algorithmically by evaluating routing table invariants (`show ip route`). The Oracle has **zero dependency on AI/LLMs**.
* **AST Anti-Drift Scoring**: Calculates the Levenshtein distance between candidate configurations and canonical fixes on the AST level. Unnecessary churn or guessing is penalized.
* **Guarded Socratic AI Mentor**: When learners request hints, local models (Ollama) or cloud LLMs are constrained by system prompts and post-generation regex filters to redact credentials and block direct syntax leaks.
* **Read-Only Web Safety**: The FastAPI server exposes exclusively `GET` endpoints, refuses non-`GET` HTTP verbs, and binds to `127.0.0.1` unless an explicit `--allow-remote` flag and bearer token are provided.

---

## 4. Module Directory & Code Organization

The codebase is organized under `src/t2t/`:

```
src/t2t/
├── __init__.py
├── config.py                 # Pydantic v2 settings, environment resolution, demo fallbacks
├── logging_setup.py          # Structured log formatters, audit trail sinks
├── cli/
│   ├── app.py                # Typer CLI commands: new-ticket, audit, status, submit, hint, demo
│   └── ui.py                 # Rich console formatters, colored telemetry tables, spinners
├── parsers/
│   ├── ast.py                # AST data structures (EigrpInstance, OspfProcess, RouteMap, PrefixList)
│   ├── cisco_iosxe.py        # Indentation-aware token parser for running-config blocks
│   └── route_parser.py       # Regex parser for 'show ip route' control-plane detail
├── audit/
│   ├── engine.py             # Rule coordinator evaluating AST against registered rules
│   ├── rules.py              # Implementation of Rules A1 through A7
│   └── models.py             # Pydantic schemas for AuditReport, Violation, and Severity
├── devices/
│   ├── session.py            # DeviceSession wrapper enforcing read_only mutation locks
│   ├── netmiko_device.py     # Live SSH transport using Netmiko/Paramiko (exclusive import)
│   └── mock.py               # Deterministic MockDevice replaying tests/fixtures CLI output
├── faults/
│   ├── catalog.py            # Pydantic validation schema for fault YAML files
│   ├── loader.py             # Loads and parses catalog YAML files (T1 through T7)
│   └── injector.py           # Pushes misconfigurations or rolls back to golden state
├── verify/
│   ├── oracle.py             # Invariant evaluator asserting protocol, next-hop, and metric
│   ├── checks.py             # Check dataclasses and baseline validation rules
│   └── invariants.py         # Domain definitions for routing convergence
├── session/
│   ├── fsm.py                # Finite State Machine (IDLE -> ACTIVE -> EVALUATING -> RESOLVED)
│   ├── service.py            # Orchestrator coordinating tickets, attempts, and verification
│   ├── scoring.py            # Exponential time-decay & AST anti-drift scoring heuristic
│   └── db.py                 # SQLite 3 WAL repository with foreign keys
├── ai/
│   ├── mentor.py             # Socratic pedagogical prompt pipeline
│   ├── redactor.py           # Pre/post-generation regex filter removing secrets & syntax
│   ├── grader.py             # Qualitative stylistic feedback generator (decoupled from grading)
│   └── ticket.py             # Scenario narrative generator
├── web/
│   ├── app.py                # FastAPI application with security middlewares & lifespan events
│   ├── routes.py             # GET-only endpoints: /api/status, /api/session, /api/history
│   └── svg.py                # Dynamic SVG renderer generating interactive colored topology links
└── demo_data/                # Bundled fallback fixtures for zero-dependency offline demos
    ├── inventory.yaml
    ├── baseline_checks.yaml
    └── catalog/
```

---

## 5. The Seven Static Audit Rules (A1–A7)

The Static Redistribution Audit Engine evaluates running configurations without touching active router hardware:

| Rule ID | Rule Name | Severity | Risk & Routing Impact | Detection Mechanism |
| :---: | :--- | :---: | :--- | :--- |
| **A1** | Missing Default Seed Metric in EIGRP | **CRITICAL** | Redistributed routes lack metric and are silently discarded. | EIGRP block has `redistribute ospf` without `metric` and no `default-metric`. |
| **A2** | Missing Subnets Keyword in OSPF | **HIGH** | Only classful network boundaries redistributed; subnets omitted. | OSPF block has `redistribute eigrp` without `subnets` argument. |
| **A3** | Mutual Redistribution Without Route Tags | **CRITICAL** | Circular re-advertising triggers routing loops and packet blackholes. | Dual redistribution present without `route-map` setting/matching numerical tags. |
| **A4** | Missing Route-Map on Redistribution | **HIGH** | Uncontrolled prefix leak; entire routing table redistributed. | `redistribute` command present without `route-map` clause. |
| **A5** | Administrative Distance Inversion | **HIGH** | ASBRs prefer suboptimal OSPF external paths over native EIGRP. | EIGRP external AD (170) exceeds OSPF AD (110) without `distance ospf external 171`. |
| **A6** | Unfiltered Default Route Injection | **MEDIUM** | Unintended default routing leads to blackholing or asymmetric paths. | Prefix-list redistributing `0.0.0.0/0` without explicit policy justification. |
| **A7** | Incomplete Route-Map Sequence (Missing Deny) | **MEDIUM** | Inadvertent catch-all permits unwanted prefixes into peer domain. | Route-map terminates on permit without explicit denial of tagged loops. |

---

## 6. Parameterized Fault Scenarios (T1–T7)

The catalog under `src/t2t/faults/catalog/` models real enterprise redistribution tickets:

1. **T1: Missing EIGRP Seed Metric** – OSPF redistributed into EIGRP on R2 without composite metric. Result: R1 receives no routes for 10.10.99.0/24.
2. **T2: OSPF Missing Subnets Keyword** – Classless subnets filtered out at redistribution boundary.
3. **T3: Administrative Distance Inversion** – Dual mutual redistribution active on R2 and R3. OSPF external AD 110 causes R3 to install suboptimal path through R2 instead of direct EIGRP path to R1.
4. **T4: Route Feedback Loop (No Tags)** – Mutual redistribution without route-maps causes routes to ping-pong between R2 and R3.
5. **T5: Inverted Route-Map Permit/Deny Logic** – Flawed route-map permits tagged routes and denies valid customer subnets.
6. **T6: Asymmetric Path Selection** – Unequal metric assignment causes suboptimal return path across inter-ASBR link.
7. **T7: Accidental Transit Domain Leak** – Branch internal loopbacks leaked into transit area without aggregation.

---

## 7. Interactive CLI Workflow & Command Reference

The platform is driven via the `t2t` CLI:

```bash
# 1. Run full offline demonstration (zero dependencies, zero routers needed)
t2t demo

# 2. Start a new troubleshooting ticket (Scenario T3)
t2t new-ticket --fault T3

# 3. Check current scenario telemetry, timer, and link health
t2t status

# 4. Run static audit against device configurations
t2t audit

# 5. Push candidate remediation and evaluate routing invariants
t2t submit --replay -e "Configured distance ospf external 171 on R3"

# 6. Request Socratic pedagogical guidance for a failed check
t2t hint

# 7. Start the read-only web dashboard and view dynamic SVG topology
t2t web --port 8000
```

---

## 8. Verification & Quality Assurance Matrix

The platform is backed by **129 automated tests** achieving a 100% pass rate:

```
============================= test session starts =============================
platform win32 -- Python 3.14.10, pytest-9.0.2, pluggy-1.6.0
collected 129 items

tests/unit/test_parsers.py ......................... [ 19%]
tests/unit/test_audit_rules.py ..................... [ 35%]
tests/unit/test_device_session.py .................. [ 49%]
tests/unit/test_fault_catalog.py ................... [ 62%]
tests/unit/test_verification_oracle.py ............. [ 75%]
tests/unit/test_scoring_engine.py .................. [ 84%]
tests/unit/test_socratic_ai.py ..................... [ 91%]
tests/unit/test_packaging.py ....................... [ 96%]
tests/unit/test_web_api.py .....                     [100%]

============================= 129 passed in 10.13s =============================
```

* **Static Type Checking**: `mypy src` passes cleanly with strict type annotations enabled across all 52 modules.
* **Code Formatting & Linting**: `ruff check .` and `ruff format .` confirm 100% PEP 8 compliance.
* **Deterministic Execution**: Zero usage of `time.sleep`; all time operations use the injectable `Clock` abstraction.
