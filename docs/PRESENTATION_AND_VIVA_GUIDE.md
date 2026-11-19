# Presentation, Viva Voce & Demonstration Defense Guide

> **Official Reviewer, Examiner & Defense Handbook for Ticket-to-Topology (`t2t`)**  
> *CCNP Enterprise (ENCOR 350-401 / ENARSI 300-410) EIGRP $\leftrightarrow$ OSPF Mutual Route Redistribution Simulator & Static Audit Platform*

---

## 1. Quick Pitch Summaries

### 30-Second Elevator Pitch
> *"Ticket-to-Topology (`t2t`) is an automated dual-mode engineering platform that solves one of the hardest problems in enterprise networking: multi-point mutual route redistribution between EIGRP and OSPF. In dual-boundary topologies, metric incompatibilities and Administrative Distance inversion (OSPF AD 110 beating EIGRP external AD 170) cause severe routing loops and suboptimal routing. Our platform combines a deterministic Cisco IOS-XE AST static audit engine, an interactive troubleshooting simulator with 7 real-world fault tickets, an independent zero-AI verification oracle, and a regex-guarded Socratic AI tutor. It runs live over SSH or 100% offline via replay fixtures, backed by 129 passing automated tests."*

### 2-Minute Executive Summary
> *"In enterprise networks, connecting distinct routing domains like EIGRP and OSPF across multiple routers is essential during corporate mergers or datacenter interconnections. However, because EIGRP uses composite metrics while OSPF uses link cost, and because OSPF AD 110 is preferred over EIGRP external AD 170, routers easily fall into circular routing loops or blackholes.*
> 
> *Current training solutions rely on passive workbooks or unguided emulators that don't verify control-plane invariants or grade configurations objectively. Furthermore, enterprise NetOps teams lack lightweight AST-aware tools to audit configurations before deployment.*
> 
> *Ticket-to-Topology introduces a dual-mode platform: First, an offline Static Redistribution Audit Engine that parses Cisco configurations into an Abstract Syntax Tree and tests them against 7 RFC-compliant rules (A1–A7) to detect missing seeds, missing tags, and AD inversion without touching live hardware. Second, a troubleshooting simulator that injects 7 parameterized faults (T1–T7) into live routers or offline mock replays. Fixes are graded by an algorithmic Verification Oracle (zero AI bias) with anti-drift penalties, while students receive guided hints from a Socratic AI mentor protected by regex filters. The system also includes an interactive real-time SVG topology web dashboard. The entire system is production-ready, strictly typed, and verified by 129 tests."*

---

## 2. Live Demonstration Script (Step-by-Step)

Follow this exact sequence during your demonstration to impress evaluators:

```bash
# -------------------------------------------------------------
# STEP 1: Execute the Zero-Dependency Replay Walkthrough
# Demonstrates pre-flight health, ticket injection, and grading
# -------------------------------------------------------------
t2t demo
```
* **What to explain to the jury**: *"Notice that `t2t demo` runs completely offline using our packaged real-router fixtures. It checks pre-flight environment health, injects a troubleshooting scenario, simulates a candidate's remediation attempt, verifies routing invariants, and awards a score—all in under 2 seconds without requiring physical router hardware."*

```bash
# -------------------------------------------------------------
# STEP 2: Start an Interactive Troubleshooting Scenario
# Injects Scenario T3 (Suboptimal Routing / AD Inversion)
# -------------------------------------------------------------
t2t new-ticket --fault T3
t2t status
```
* **What to explain**: *"Here we initialize Scenario T3. The FSM transitions to ACTIVE and starts our countdown timer. The telemetry table displays the active ticket ID, target devices (R2 and R3 ASBRs), and the problem statement: OSPF external routes are overriding EIGRP external routes on R3."*

```bash
# -------------------------------------------------------------
# STEP 3: Run the Static Redistribution Audit Engine
# Demonstrates offline AST linting against Rules A1–A7
# -------------------------------------------------------------
t2t audit
```
* **What to explain**: *"We run `t2t audit`. Under the hood, our Cisco IOS-XE parser parses the running-config into a hierarchical AST. The engine immediately flags **Rule A5: Administrative Distance Inversion** as a High Severity violation, warning that OSPF AD 110 will defeat EIGRP external AD 170 unless distance tuning is applied."*

```bash
# -------------------------------------------------------------
# STEP 4: Query the Socratic AI Mentor
# Demonstrates pedagogical guidance with regex secret redaction
# -------------------------------------------------------------
t2t hint
```
* **What to explain**: *"When a candidate is stuck, they request a hint. Notice the mentor does NOT give away the CLI answer. It asks a targeted Socratic question: 'How does R3 determine which path to prefer when it receives prefix 10.10.99.0/24 from both EIGRP and OSPF? Compare their Administrative Distances.' Furthermore, our regex filter strips any router passwords or IP credentials before they ever reach the model."*

```bash
# -------------------------------------------------------------
# STEP 5: Submit Candidate Remediation
# Demonstrates Verification Oracle and Anti-Drift Scoring
# -------------------------------------------------------------
t2t submit --replay -e "Configured distance ospf external 171 on R3 to ensure EIGRP external path is preferred."
```
* **What to explain**: *"The candidate submits the remediation. The Verification Oracle checks the routing table for `10.10.99.0/24`. All invariant checks pass (`PASS`). The scoring engine evaluates time decay and calculates the AST Levenshtein edit distance between the candidate's commands and the canonical fix. Because there is zero unnecessary configuration churn, the student receives full marks (98.5/100)."*

```bash
# -------------------------------------------------------------
# STEP 6: Launch the Read-Only SVG Web Dashboard
# Demonstrates real-time visual telemetry and safety guards
# -------------------------------------------------------------
t2t web --port 8000
```
* **What to explain**: *"Finally, we launch `t2t web`. We open `http://127.0.0.1:8000`. The browser renders an interactive SVG topology. Links are dynamically colored green for verified paths, amber for warnings, and red for active failures. Notice that our web API contains ZERO mutation endpoints—it is strictly GET-only to prevent unauthorized network changes."*

---

## 3. Top 15 Viva Voce & Technical Defense Questions

### Q1: What is the primary problem Ticket-to-Topology solves?
**Answer**:
> *"Ticket-to-Topology solves the lack of deterministic verification, automated configuration linting, and guided troubleshooting in multi-point mutual route redistribution between EIGRP and OSPF. In dual-boundary networks, metric incompatibility and Administrative Distance inversion frequently cause routing loops and suboptimal routing. `t2t` provides an AST-based static audit engine (Rules A1–A7) and an interactive simulator with 7 calibrated fault tickets (T1–T7), an independent verification oracle, and a guarded Socratic AI mentor."*

### Q2: Explain Administrative Distance Inversion and why it occurs between EIGRP and OSPF.
**Answer**:
> *"Administrative Distance (AD) is Cisco's measure of route trustworthiness. Internal EIGRP is AD 90, OSPF is flat AD 110, and External EIGRP (redistributed) is AD 170. When ASBR-1 (R2) redistributes an EIGRP prefix into OSPF, it enters OSPF with AD 110. When ASBR-2 (R3) receives this route via OSPF (AD 110) and also directly from the branch via EIGRP External (AD 170), R3 prefers the lower AD (110 < 170). Consequently, R3 sends traffic intended for the branch through R2 instead of its direct link. This is AD Inversion, and it leads to suboptimal paths and route feedback."*

### Q3: What are the three classic engineering remedies for dual-point redistribution?
**Answer**:
> *"1. **Default Seed Metrics**: Explicitly configuring metrics (`default-metric 10000 100 255 1 1500` in EIGRP or `subnets` in OSPF) so redistributed routes are not dropped.*  
> *2. **Route Tagging with Route-Maps**: Stamping routes with tags (e.g., `set tag 110` when entering OSPF) and denying routes with that tag when redistributing back into EIGRP (`match tag 110` -> `deny`).*  
> *3. **Administrative Distance Tuning**: Modifying OSPF external distance on the ASBRs via `distance ospf external 171`. Because 170 (EIGRP external) is now lower than 171, the ASBR will always prefer the native EIGRP path over the redistributed OSPF path."*

### Q4: Why did you build an AST parser instead of using regular expressions?
**Answer**:
> *"Cisco IOS-XE configuration syntax is hierarchical and indentation-sensitive. A command like `redistribute ospf 1 metric 1000 100 255 1 1500` or `default-metric` has meaning only within the context of its parent `router eigrp 100` block. Flat regex search across a raw config file cannot reliably determine which process a sub-command belongs to, especially when multiple EIGRP autonomous systems or OSPF processes exist on the same router. Our AST parser tracks indentation, tokenizes parent blocks, and maps statements to strongly-typed domain objects (`EigrpInstance`, `OspfProcess`, `RouteMapEntry`, `PrefixList`), enabling deterministic rule evaluation."*

### Q5: Why is the Verification Oracle strictly decoupled from AI / LLMs (AGENTS.md Rule 3)?
**Answer**:
> *"Language models are probabilistic and prone to hallucinations; they cannot be trusted to grade routing table invariants objectively. If an LLM is used to decide pass or fail, the grading would be non-deterministic and violate academic integrity. In `t2t`, pass/fail is evaluated 100% deterministically by querying the control plane (`show ip route <prefix>`) and verifying protocol, next-hop IP, and metric mathematically. AI is used solely as a pedagogical mentor for qualitative hints and explanations."*

### Q6: How does the AST Anti-Drift Scoring algorithm work?
**Answer**:
> *"Standard simulators only check whether reachability is restored, allowing students to blindly guess or copy-paste 50 irrelevant lines until tests pass. Our scoring engine computes the normalized Levenshtein edit distance between the candidate's AST and the canonical minimal fix. We tolerate 15% cosmetic variation, but any superfluous commands, erroneous route-maps, or configuration churn incur steep penalties. This base score is multiplied by an exponential time-decay factor: score remains 100% during the first half of the allotted time and decays exponentially if the student takes longer."*

### Q7: How does the Socratic AI Mentor work, and how do you prevent answer leaks?
**Answer**:
> *"The AI mentor is built on a two-stage guardrail architecture. First, system prompt engineering instructs the model to act as a Socratic tutor—asking guiding diagnostic questions about metric propagation or AD hierarchies rather than writing configuration syntax. Second, a post-generation regex redaction pipeline scans the output for Cisco command patterns (e.g., `router eigrp`, `route-map`, `distance ospf`, passwords, and IP addresses) and replaces them with `[REDACTED]`. This ensures the student must perform the cognitive synthesis themselves."*

### Q8: What is SQLite Write-Ahead Logging (WAL) and why was it chosen?
**Answer**:
> *"SQLite in default rollback journal mode locks the entire database during write transactions, causing concurrency contention between the CLI process, background audit logs, and the web telemetry server. In WAL mode (`PRAGMA journal_mode=WAL`), writers append changes to a separate `-wal` file while readers query the main database concurrently without blocking. WAL provides true ACID compliance, high read concurrency for the FastAPI server, and crash resilience without requiring a heavy MySQL or PostgreSQL daemon."*

### Q9: Why is the FastAPI web server strictly read-only and GET-only?
**Answer**:
> *"Exposing configuration push or mutation endpoints over HTTP without enterprise-grade mutual TLS and OAuth2 authentication presents a catastrophic security vulnerability, allowing remote attackers to alter router configurations. To ensure absolute safety, all `/api/*` endpoints are strictly GET-only (`/api/status`, `/api/session`, `/api/history`, `/api/audit/latest`). Our test suite includes a contract test (`test_u10_2`) that automatically fails if any POST, PUT, PATCH, or DELETE route is added. Furthermore, the server binds to `127.0.0.1` and refuses `0.0.0.0` unless an explicit `--allow-remote` flag and bearer token are supplied."*

### Q10: How does the MockDevice replay engine work without physical routers?
**Answer**:
> *"Per AGENTS.md Rule 5, tests must use real captured router outputs, never synthetic inventions. We recorded authentic Cisco IOS-XE CLI outputs across all 4 routers in baseline, faulty, and remediated states into `tests/fixtures/`. The `MockDevice` implements the exact same `DeviceProtocol` interface as `NetmikoDevice`. When `send_command('show ip route')` is called, `MockDevice` matches the command and active scenario to return the exact raw fixture. This allows complete, deterministic qualification in <2 seconds on any standard laptop without physical routers or virtual machine overhead."*

### Q11: What are the 7 Static Audit Rules (A1–A7)?
**Answer**:
> *"• **A1**: Missing EIGRP default seed metric (Critical).*  
> *• **A2**: Missing OSPF `subnets` keyword (High).*  
> *• **A3**: Mutual redistribution without route tagging (Critical).*  
> *• **A4**: Mutual redistribution without a route-map (High).*  
> *• **A5**: Administrative Distance inversion without distance tuning (High).*  
> *• **A6**: Unfiltered default route injection (`0.0.0.0/0`) (Medium).*  
> *• **A7**: Incomplete route-map sequence lacking explicit deny for looped tags (Medium)."*

### Q12: How did you ensure test determinism and avoid `time.sleep`?
**Answer**:
> *"AGENTS.md Rule 10 strictly prohibits `time.sleep` in library code and unit tests. Flaky tests occur when tests rely on wall-clock sleeps for timeouts. We engineered an injectable `Clock` protocol (`SystemClock` for live runtime, `MockClock` for testing). When testing timeout transitions, session expiration, or time decay, the test advances `MockClock.advance(seconds=120)` instantaneously. As a result, our entire 129-test suite executes in just 10.13 seconds with 100% determinism."*

### Q13: What happens if an engineer submits a fix that restores reachability but creates a routing loop?
**Answer**:
> *"Simple ping-based testing might falsely report that the network is 'working' because packets might reach the destination despite traversing an inefficient 5-hop path or flapping across ASBRs. Our Verification Oracle inspects the internal control-plane routing table on every router in the path. It asserts that the route protocol is strictly `eigrp` on branch nodes, `ospf` on HQ nodes, and that the next-hop IP points directly across the primary link rather than the inter-ASBR link. If a route loops or takes a suboptimal transit path, the check fails immediately."*

### Q14: How does this project align with Cisco certification syllabi?
**Answer**:
> *"It maps directly to **CCNP Enterprise ENCOR (350-401) Section 3.2** (configure and verify route redistribution between any routing protocols) and **CCNP Enterprise ENARSI (300-410) Section 1.2** (troubleshoot route redistribution, route-maps, prefix-lists, tags, and administrative distance). It covers the most challenging troubleshooting tickets found in the actual Cisco live lab exams."*

### Q15: What are the primary limitations and future roadmap?
**Answer**:
> *"Currently, the platform specializes in a 4-router dual-boundary IPv4 topology running Cisco IOS-XE CLI syntax. Future enhancements include: (1) multi-protocol BGP EVPN/VXLAN redistribution for datacenter interconnects, (2) multi-vendor OpenConfig/YANG modeling for Arista EOS and Juniper Junos, (3) an opt-in web terminal (xterm.js) for browser CLI interaction, and (4) automated Containerlab integration for dynamic topology spinning."*

---

## 4. Evaluation Rubric & Scoring Expectations

| Evaluation Dimension | Weight | Key Evidence in `t2t` |
| :--- | :---: | :--- |
| **Architectural Rigor** | 25% | Multi-tier layering (Presentation, Domain, Infrastructure); loose coupling via `DeviceProtocol`; FSM session management; SQLite WAL mode. |
| **Algorithmic Complexity** | 20% | Indentation-aware AST grammar parser; 7 deterministic audit algorithms; AST Levenshtein anti-drift scoring; exponential time decay. |
| **Testing & Verification** | 25% | Test-Driven Development (TDD); 10 formal phase gates (U1.1–U10.3); 129/129 tests passing in 10.13s; 100% mypy static type safety; ruff compliance. |
| **Innovation & Usability** | 15% | Guarded Socratic AI mentor with regex secret redactor; read-only FastAPI server; dynamic SVG colored topology canvas; zero-dependency offline replay. |
| **Documentation & Defense** | 15% | Comprehensive 30-page university report; detailed architecture manuals; presentation guide; IEEE citations; strict anti-plagiarism compliance. |
