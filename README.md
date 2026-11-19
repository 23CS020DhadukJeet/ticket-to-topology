# Ticket-to-Topology (t2t)

[![CI Release](https://github.com/jeetdhaduk/ticket-to-topology/actions/workflows/release.yml/badge.svg)](https://github.com/jeetdhaduk/ticket-to-topology/actions)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checked: Mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://mypy-lang.org/)
[![Tests: 127 Passing](https://img.shields.io/badge/tests-127%20passed-brightgreen.svg)](tests/)

> **Dual-mode troubleshooting simulator and production configuration audit engine for EIGRP $\leftrightarrow$ OSPF mutual route redistribution on Cisco IOS-XE.**  
> Designed for CCNP Enterprise (**ENCOR 350-401** & **ENARSI 300-410**) engineers, network architects, and NetDevOps automation teams.

---

## 📑 Table of Contents

1. [Executive Overview](#-executive-overview)
2. [How It Works: Core Architecture](#-how-it-works-core-architecture)
3. [Complete Project Structure](#-complete-project-structure)
4. [Phase-by-Phase Technical Implementation](#-phase-by-phase-technical-implementation)
5. [End-to-End Troubleshooting Workflow](#-end-to-end-troubleshooting-workflow)
6. [Production Static Audit Workflow](#-production-static-audit-workflow)
7. [How to Run the Project (Step-by-Step)](#-how-to-run-the-project-step-by-step)
   - [Mode 1: Instant 90-Second Demo](#mode-1-instant-90-second-demo-zero-setup)
   - [Mode 2: Full Offline Simulation (Replay Mode)](#mode-2-full-offline-simulation-replay-mode)
   - [Mode 3: Live Real-Time Web Dashboard & Topology API](#mode-3-live-real-time-web-dashboard--topology-api)
   - [Mode 4: Running Production Audits](#mode-4-running-production-audits)
   - [Mode 5: Live Hardware / EVE-NG / GNS3 Lab Mode](#mode-5-live-hardware--eve-ng--gns3-lab-mode)
   - [Mode 6: Docker & Docker Compose Deployment](#mode-6-docker--docker-compose-deployment)
8. [CLI Command Reference](#-cli-command-reference)
9. [Configuration & Environment Variables](#-configuration--environment-variables)
10. [Test Suite, Quality Gates & CI/CD](#-test-suite-quality-gates--cicd)

---

## 🎯 Executive Overview

Mutual route redistribution across autonomous system boundary routers (ASBRs) is among the most catastrophic failure domains in enterprise IP networking:
- **Suboptimal Routing & Asymmetric Paths:** Differing Administrative Distances (AD) cause traffic to traverse slower or suboptimal paths.
- **Routing Feedback Loops:** Routes learned from OSPF and injected into EIGRP can be redistributed back into OSPF with artificial metrics, creating routing loops and blackholes.
- **Metric Collapse:** Forgetting EIGRP K-metrics on redistribution completely prevents route installation.
- **Classful Mask Collapse:** Omitting the `subnets` keyword in OSPF silently drops non-classful prefixes.

`t2t` delivers two battle-tested engines to solve this:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            TICKET-TO-TOPOLOGY (t2t)                         │
├─────────────────────────────────────────┬───────────────────────────────────┤
│    MODE 1: TROUBLESHOOTING SIMULATOR    │      MODE 2: STATIC AUDIT ENGINE  │
├─────────────────────────────────────────┼───────────────────────────────────┤
│ • Injects realistic CCNP faults (T1-T10)│ • Statically audits Cisco running │
│ • Generates non-technical user tickets  │   configurations against A1–A7    │
│ • Socratic AI mentor (3 tiered hints)   │ • Zero packet/network dependency  │
│ • Strict deterministic verification     │ • AST route-map & prefix parsing  │
│ • Anti-drift clean configuration check  │ • Formats: Rich Table, JSON, MD   │
│ • Deterministic scoring with time-decay │ • JSON Schema validation          │
│ • 100% offline replay fixture support   │ • Automated CI/CD gate exit codes │
└─────────────────────────────────────────┴───────────────────────────────────┘
```

---

## 🏗️ How It Works: Core Architecture

The architecture enforces strict separation of concerns, guarantees deterministic grading, and ensures zero network mutations during audits.

```
                           ┌────────────────────────────┐
                           │   CLI / Web / REPL Entry   │
                           │ (Typer CLI + FastAPI Web)  │
                           └──────────────┬─────────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
       ┌─────────────────────┐                         ┌─────────────────────┐
       │   Session Service   │                         │    Audit Service    │
       │ (State Machine, DB) │                         │  (Rules Engine A1-7)│
       └──────────┬──────────┘                         └──────────┬──────────┘
                  │                                               │
        ┌─────────┴─────────┐                                     │
        ▼                   ▼                                     ▼
┌──────────────┐    ┌──────────────┐                    ┌──────────────────┐
│  AI Engine   │    │Verify Engine │                    │ Device Parser &  │
│(Ticket/Mentor│    │ (Pure Route  │                    │ DeviceModel AST  │
│ Scorer/Sink) │    │ & Ping Oracle│                    └─────────┬────────┘
└──────────────┘    └───────┬──────┘                              │
                            │                                     │
                            └──────────────────┬──────────────────┘
                                               ▼
                                   ┌──────────────────────┐
                                   │    Device Session    │
                                   │  (Single Gatekeeper) │
                                   └───────────┬──────────┘
                                               │
                        ┌──────────────────────┴──────────────────────┐
                        ▼                                             ▼
             ┌─────────────────────┐                       ┌─────────────────────┐
             │  NetmikoDevice      │                       │  MockDevice         │
             │  (Live SSH/Lab)     │                       │  (Offline Fixtures) │
             └─────────────────────┘                       └─────────────────────┘
```

### Architectural Invariants (`AGENTS.md`)
1. **Zero Netmiko Leakage:** Only `src/t2t/devices/netmiko_device.py` is permitted to import Netmiko. All higher layers talk to the abstract `Device` protocol.
2. **Pure Deterministic Verification:** The test result (PASS/FAIL) and score are decided **only** by `t2t.verify`. `t2t.verify`, `t2t.faults`, `t2t.session.scoring`, and `t2t.audit` **never import `t2t.ai`**.
3. **Single Configuration Gateway:** All device mutations must pass through `DeviceSession.push_config`. The audit service uses read-only devices and cannot mutate routers.
4. **Declarative Fault Catalog:** Faults are strictly defined in YAML (`src/t2t/faults/catalog/*.yaml`). No fault logic is ever hard-coded in Python.
5. **Redaction & Secret Protection:** Passwords, tokens, and SSH keys are masked as `SecretStr` and filtered from all logs, tracebacks, and AI prompts.

---

## 📂 Complete Project Structure

Here is the complete file and directory layout of the repository:

```
ticket-to-topology/
├── .github/
│   └── workflows/
│       ├── ci.yml                     # Offline tests, ruff, mypy across Python 3.11/3.12
│       └── release.yml                # CI/CD: build wheel, Docker image, GH Release, MkDocs
├── docs/                              # Full MkDocs Material documentation site
│   ├── index.md                       # Home & feature overview
│   ├── quickstart.md                  # 10-minute setup and quick guide
│   ├── architecture.md                # Layered design, invariants, data flows
│   ├── lab-guide.md                   # EVE-NG/GNS3 setup, cabling, topology
│   ├── fault-authoring.md             # How to create new YAML fault scenarios
│   ├── audit-rules.md                 # Documentation for rules A1 through A7
│   ├── runbook.md                     # Operator runbook, state resets, recovery
│   ├── performance.md                 # Convergence timings, latency, benchmarks
│   ├── faq.md                         # Frequently asked questions & troubleshooting
│   └── BUILD_GUIDE.md                 # Master phase-by-phase implementation manual
├── lab/                               # Lab orchestration, automation scripts & golden templates
│   ├── golden/                        # Cisco IOS-XE Jinja2 golden baseline templates
│   │   ├── R1.cfg.tpl                 # Branch router template
│   │   ├── R2.cfg.tpl                 # ASBR-1 template
│   │   ├── R3.cfg.tpl                 # ASBR-2 template
│   │   └── R4.cfg.tpl                 # HQ core router template
│   ├── golden_source/                 # Raw baseline configs captured from live lab
│   ├── inventory.example.yaml         # Example router connection credentials
│   └── scripts/
│       ├── capture_fixtures.py        # Captures live IOS-XE output into test fixtures
│       ├── render_golden.py           # Renders golden configs with environment passwords
│       ├── reset_cycles.py            # Tests 10 consecutive inject-revert cycles for drift
│       ├── soak.py                    # Multi-hour reliability and convergence soak runner
│       └── learner_bot.py             # Autonomous agent simulating learner troubleshooting
├── src/t2t/                           # Main Python package
│   ├── __init__.py                    # Package metadata & version
│   ├── models.py                      # Global data models and enumerations
│   ├── clock.py                       # Injectable Clock protocol (SystemClock, FakeClock)
│   ├── config.py                      # Pydantic Settings, Inventory loader, SecretStr masking
│   ├── errors.py                      # Typed exceptions (T2TError hierarchy) & exit codes
│   ├── logging_setup.py               # Redacting filter, JSON formatting, correlation IDs
│   ├── ai/                            # Socratic AI Layer (LLM integration)
│   │   ├── factory.py                 # LLM provider factory (Ollama, OpenAI, Claude, None)
│   │   ├── providers.py               # Transport implementations with retries and backoff
│   │   ├── redactor.py                # Regex engine redacting passwords/keys before LLM
│   │   ├── ticket.py                  # Generates non-technical support tickets from YAML
│   │   ├── mentor.py                  # Delivers 3-level hints without revealing the fix
│   │   ├── grader.py                  # Evaluates learner explanation against CCNP concepts
│   │   ├── sink.py                    # Audits all prompt/response interactions to SQLite
│   │   └── prompts/                   # Sanitized prompt templates
│   │       ├── ticket_v1.txt
│   │       ├── mentor_v1.txt
│   │       └── grader_v1.txt
│   ├── audit/                         # Static Redistribution Audit Engine
│   │   ├── model.py                   # AST parser transforming raw configs to DeviceModel
│   │   ├── rules.py                   # Pure rule implementations: A1 to A7
│   │   ├── service.py                 # AuditService orchestrating file/live audits
│   │   ├── report.py                  # Report formatters: Rich Table, Markdown, JSON
│   │   └── report.schema.json         # Formal JSON Schema for audit reports
│   ├── cli/                           # Command Line Interface Layer
│   │   ├── app.py                     # Typer CLI application root and command handlers
│   │   └── ui.py                      # Rich terminal cards, tables, panels, formatting
│   ├── demo_data/                     # Packaged offline fixtures for out-of-the-box demo
│   │   ├── baseline/                  # Baseline router show outputs for R1-R4
│   │   └── faulted/T3/                # Faulted outputs for T3 scenario
│   ├── devices/                       # Device Abstraction Layer
│   │   ├── base.py                    # Device Protocol (send_show, push_config, close)
│   │   ├── netmiko_device.py          # Real SSH transport (the ONLY Netmiko import)
│   │   ├── mock_device.py             # Offline fixture-backed Device implementation
│   │   ├── session.py                 # DeviceSession manager & command audit log
│   │   └── slug.py                    # Deterministic, collision-free command slugifier
│   ├── faults/                        # Fault Engine & Scenario Catalog
│   │   ├── baseline.yaml              # Global golden oracle checks (routes, hops, ping)
│   │   ├── engine.py                  # Injects faults, tracks state, executes rollback
│   │   ├── loader.py                  # Validates YAML schema, reject missing revert blocks
│   │   ├── qualify.py                 # Fault qualification harness (proves baseline/fault)
│   │   ├── settle.py                  # Routing convergence poll loop with exponential backoff
│   │   ├── state.py                   # Atomically manages .t2t/state.json with file locking
│   │   └── catalog/                   # Validated CCNP Fault Scenarios (T1 to T10)
│   │       ├── T1.yaml                # Suboptimal metric / missing metric type
│   │       ├── T2.yaml                # Missing EIGRP K-metrics on redistribution
│   │       ├── T3.yaml                # Distance inversion causing feedback routing loop
│   │       ├── T4.yaml                # Missing 'subnets' keyword in OSPF redistribution
│   │       ├── T5.yaml                # Route-map filter dropped prefix (deny statement)
│   │       ├── T6.yaml                # Tag loop prevention failure / route reflection
│   │       ├── T7.yaml                # Passive interface suppressing redistribution next-hop
│   │       ├── T8.yaml                # Metric-type 1 vs 2 cost calculation conflict
│   │       ├── T9.yaml                # Access-list wildcard mask syntax inversion
│   │       └── T10.yaml               # Administrative distance race condition across ASBRs
│   ├── parsers/                       # Cisco IOS-XE Text Parsers
│   │   ├── route.py                   # Parses 'show ip route' & 'show ip route <pfx>'
│   │   ├── neighbors.py               # Parses 'show ip ospf neighbor' & 'show ip eigrp neighbors'
│   │   ├── routemap.py                # Parses 'show route-map' clauses and sequences
│   │   └── config.py                  # Normalizes running-configs for AST comparison
│   ├── session/                       # Troubleshooting Session Orchestrator
│   │   ├── models.py                  # SessionRecord, AttemptRecord, HintRecord models
│   │   ├── state.py                   # Finite State Machine (IDLE -> ACTIVE -> VERIFYING)
│   │   ├── store.py                   # SQLite database manager (WAL mode, migrations)
│   │   ├── scoring.py                 # Deterministic scoring algorithm with time-decay
│   │   ├── drift.py                   # Normalizes configs & detects configuration drift
│   │   └── service.py                 # Core SessionService coordinating simulator lifecycle
│   ├── verify/                        # Technical Verification Oracle
│   │   ├── checks.py                  # RouteCheck, NeighborCheck, PingCheck, ConfigCheck
│   │   └── engine.py                  # Evaluates baseline checks, detects flapping/instability
│   └── web/                           # Read-Only Web Dashboard & API (Phase 10)
│       ├── __init__.py                # Web package exports
│       └── app.py                     # FastAPI application, GET-only routes, SVG topology
├── tests/                             # Comprehensive Automated Test Suite
│   ├── unit/                          # 127 Unit & Contract Tests
│   │   ├── test_ai.py                 # Prompt injection, redaction, provider fallback
│   │   ├── test_audit_cli.py          # Audit exit codes (0/1/2), schema validation, flags
│   │   ├── test_audit_model.py        # Config AST parsing & DeviceModel extraction
│   │   ├── test_audit_rules.py        # Unit tests for rules A1 through A7
│   │   ├── test_cli_replay.py         # End-to-end replay troubleshooting CLI workflow
│   │   ├── test_clock.py              # FakeClock virtual time progression
│   │   ├── test_devices.py            # MockDevice, Netmiko retries, read-only blocks
│   │   ├── test_doctor.py             # Pre-flight doctor checks and command parser
│   │   ├── test_drift.py              # Configuration normalization & drift detection
│   │   ├── test_fault_engine.py       # Fault injection, rollback, state lock protection
│   │   ├── test_fault_loader.py       # YAML catalog validation & schema enforcement
│   │   ├── test_golden.py             # Golden template security & placeholder assertions
│   │   ├── test_hardening.py          # Chaos tests, typed exceptions, correlation IDs
│   │   ├── test_logging.py            # Log rotation, redaction filter, JSON logs
│   │   ├── test_packaging.py          # Wheel installation smoke & Docker container test
│   │   ├── test_parsers.py            # Regex parsers for routes, neighbors, route-maps
│   │   ├── test_scoring.py            # Time decay, hint penalty, floor clamping
│   │   ├── test_session.py            # DeviceSession push_config and command logging
│   │   ├── test_session_service.py    # State transitions, concurrency locks, hint caps
│   │   ├── test_settle.py             # Routing convergence polling & timeout guards
│   │   ├── test_slug.py               # Deterministic command slug collision tests
│   │   ├── test_smoke.py              # Versioning and basic imports
│   │   ├── test_store.py              # SQLite WAL mode, schema v1->v2 migrations
│   │   ├── test_ui.py                 # Rich terminal components rendering
│   │   ├── test_verify.py             # Technical checks: route presence, hops, stability
│   │   └── test_web.py                # U10.1 contract, U10.2 GET-only, U10.3 bind refusal
│   ├── integration/                   # Live Lab Integration Tests (@pytest.mark.lab)
│   │   ├── test_devices_lab.py        # Live Netmiko SSH connection to routers
│   │   ├── test_faults_lab.py         # Live fault injection and revert on Cisco IOS-XE
│   │   └── test_oracle_lab.py         # Live verification of golden redistribution baseline
│   └── synthetic/                     # Synthetic test fixtures for edge-case unit tests
├── .dockerignore                      # Docker build exclusions
├── .env.example                       # Template for environment configuration
├── .gitignore                         # Git ignored files (state, databases, venv)
├── .pre-commit-config.yaml            # Git hooks: ruff, mypy, detect-secrets
├── CHANGELOG.md                       # Version changelog
├── CONTRIBUTING.md                    # Guidelines for contributors & developers
├── docker-compose.yml                 # Orchestration for t2t, t2t-web, and Ollama AI
├── Dockerfile                         # Multi-stage, non-root hardened Docker container
├── LICENSE                            # MIT License
├── mkdocs.yml                         # MkDocs Material configuration
├── pyproject.toml                     # Modern PEP 621 package specification
└── README_NEW.md                      # Comprehensive Master Documentation (This file)
```

---

## ⚙️ Phase-by-Phase Technical Implementation

`ticket-to-topology` was built across 10 disciplined, test-driven phases:

### Phase 0 — Foundations & Quality Rigor
- Strict typing (`mypy --strict`), Ruff linting/formatting, pre-commit hooks, and secret scanning (`detect-secrets`).
- Zero-tolerance baseline: clean exits, explicit timeouts, and zero unhandled exceptions.

### Phase 1 — Lab Topology & Golden Templates
- 4-Router mutual redistribution topology:
  - **R1 (Branch):** Running EIGRP AS 100.
  - **R2 & R3 (ASBRs):** Dual-stack boundary routers redistributing EIGRP $\leftrightarrow$ OSPF with route-maps, metric tags, and administrative distance tuning (`distance ospf external 171`).
  - **R4 (HQ Core):** Running OSPF Area 0.
- Jinja2 golden templates (`lab/golden/*.cfg.tpl`) sanitized to ensure zero plaintext credentials exist in git.

### Phase 2 — Safe Device Abstraction Layer
- Built the `Device` Protocol.
- Created `NetmikoDevice` — the **only** module in the entire project permitted to import Netmiko. Features 3 retries with exponential backoff, per-command read timeouts, and a hard `read_only` guard that blocks any configuration commands before touching the wire.
- Built `MockDevice` allowing 100% offline simulation using deterministic fixture lookups.
- Implemented `DeviceSession` as the single gatekeeper for pushing router configurations and auditing every sent command.

### Phase 3 — Technical Verification Oracle
- Declarative verification engine reading `baseline.yaml`:
  - `RouteCheck`: Verifies prefix presence, prefix absence, prefix mask, protocol type, and exact next hops.
  - `NeighborCheck`: Verifies OSPF `FULL` state and EIGRP adjacencies.
  - `PingCheck`: Validates end-to-end data plane reachability.
  - `RouteMapClauseCheck`: Inspects route-map sequence tags and permits.
- Flapping detection: samples routing state over time using an injectable virtual `Clock` to catch route oscillation.

### Phase 4 — Fault Injection & Rollback Engine
- Created 10 realistic CCNP fault scenarios (`T1`–`T10`) defined purely in YAML with exact inject and revert command sets.
- Built `FaultEngine` with two-phase rollback: if any check fails during injection, it automatically triggers rollback.
- Added file-backed state locking (`.t2t/state.json`) with PID tracking to prevent concurrent conflicting sessions.
- Added qualification harness (`t2t qualify --fault T3`) proving that faults break the baseline and revert restores it cleanly.

### Phase 5 — Socratic AI Pedagogical Layer
- Integrated multi-provider LLM support: local Ollama (`llama3:8b`), OpenAI (`gpt-4o-mini`), Anthropic Claude, and offline deterministic fallback.
- **Security Guardrails:**
  - Automated regex redactor strips IP addresses, passwords, and private keys before calling external models.
  - Banned-term filter ensures the AI mentor never gives away the direct CLI command or answer.
  - Prompt injection sink audits all LLM transactions into SQLite (`t2t.db`).
- **Strict Invariant:** Zero AI in PASS/FAIL decisions. Grading is purely technical.

### Phase 6 — Session Orchestrator & CLI UX
- State machine managing learner progression: `IDLE` $\to$ `ACTIVE` $\to$ `VERIFYING` $\to$ `SOLVED` / `ABANDONED`.
- SQLite storage with Write-Ahead Logging (WAL) and automatic schema migrations.
- Dynamic scoring algorithm:
  - Base score: 100 points.
  - Time decay: gradual decay towards par time with zero bonus past $2\times\text{par}$.
  - Hint penalties: $-10$ for Hint 1, $-20$ for Hint 2, $-30$ for Hint 3.
  - Unverified or revealed attempts receive exactly 0 points.
- **Anti-Drift Engine:** AST-normalizes running configurations (ignores whitespace, comment lines, and reordered ACL statements) to detect candidate configuration drift.

### Phase 7 — Production Static Audit Engine
- Standalone static configuration analyzer targeting Cisco IOS-XE syntax.
- Parses configs into an abstract syntax tree (`DeviceModel`).
- Evaluates 7 formal CCNP redistribution rules:
  - **A1:** Redistribution without a route-map filter.
  - **A2:** EIGRP redistribution missing seed K-metrics (`default-metric`).
  - **A3:** OSPF redistribution missing the `subnets` keyword.
  - **A4:** Mutual redistribution missing route tagging loop guards.
  - **A5:** OSPF external distance inversion (`distance ospf external 171` missing).
  - **A6:** Route-maps with missing permit clauses or broken prefix-list references.
  - **A7:** Redistribution metric type inconsistencies (E1 vs E2).
- Validated against formal JSON Schema (`src/t2t/audit/report.schema.json`).
- Stable exit codes for CI/CD pipelines (0 = clean, 1 = violations above threshold, 2 = usage error).

### Phase 8 — Enterprise Hardening & Reliability
- Typed exception hierarchy rooted at `T2TError` with user-friendly messages and predictable exit codes.
- Redacted logging with rotating log files (`logs/t2t.log`) and correlation IDs (`X-Correlation-ID`) across concurrent operations.
- `--strict-host-keys` flag for hardened SSH validation.
- Soak testing harness (`lab/scripts/soak.py`) and chaos tests proving resilience under network partitions.

### Phase 9 — Packaging, Documentation & Deployment
- Finalized PEP 621 `pyproject.toml` (version `1.0.0`).
- Self-contained offline demo fixtures packaged into `src/t2t/demo_data/`.
- Multi-stage, non-root hardened `Dockerfile` with `/data` volume ownership fix.
- Docker Compose configuration orchestrating `t2t`, `t2t-web`, and `ollama`.
- MkDocs Material documentation site publishing to GitHub Pages.

### Phase 10 — Read-Only Web Dashboard & Topology API
- Read-only FastAPI service under `src/t2t/web/app.py`.
- **GET-only Contract Endpoints:** `/api/status`, `/api/session`, `/api/history`, `/api/audit/latest`.
- **Zero Mutation Endpoints:** Strictly refuses any POST, PUT, DELETE, or PATCH methods.
- **Security Bind Guard:** Binds to `127.0.0.1` by default; strictly refuses `0.0.0.0` unless both `--allow-remote` **and** a secure bearer token are provided.
- Standalone dark-mode HTML/JS single-page dashboard with real-time SVG topology displaying link health (green/amber/red) polling every 3 seconds.

---

## 🔄 End-to-End Troubleshooting Workflow

Here is how a network engineer uses `t2t` to diagnose and resolve an incident:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. PRE-FLIGHT CHECK: t2t doctor --replay                                    │
│    Verifies all 4 routers, SSH, IOS-XE versions, and golden flash backups.  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ 2. DISPATCH INCIDENT: t2t new-ticket --fault T3                             │
│    Injects fault T3 into the lab and formats non-technical user ticket:     │
│    "HQ finance servers cannot reach Branch payroll subnet 10.10.99.0/24..." │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ 3. TRIAGE & TOPOLOGY CHECK: t2t status                                      │
│    Displays matrix of all 5 key prefixes across R1, R2, R3, R4.             │
│    Identifies 10.10.99.0/24 missing on R3 or learned with bad AD.           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ 4. REQUEST MENTOR GUIDANCE: t2t hint                                        │
│    Level 1 Hint: "Notice the AD of external OSPF routes vs external EIGRP." │
│    Level 2 Hint: "What happens when R3 redistributes OSPF back to EIGRP?"   │
│    Level 3 Hint: "Review 'distance ospf external' command syntax."          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ 5. APPLY CLI REMEDIATION: (SSH to router R3 or CLI push)                    │
│    router ospf 1                                                            │
│     distance ospf external 171                                              │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ 6. SUBMIT & VERIFY: t2t submit -e "Restored distance ospf external 171"    │
│    • Evaluates technical route & ping oracle checks.                        │
│    • Compares running config with baseline to ensure zero drift.            │
│    • Grades technical explanation and outputs final score breakdown.        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Production Static Audit Workflow

Auditing enterprise configurations before deployment takes seconds:

```bash
# Audit an entire folder of router configs against rules A1–A7
t2t audit --from-dir ./configs --format table

# Enforce CI/CD quality gate (fail pipeline if any High severity issue exists)
t2t audit --from-dir ./configs --fail-on High

# Export structured JSON report for security compliance
t2t audit --from-dir ./configs --format json --output audit-report.json
```

Sample audit table output:
```text
                       Cisco IOS-XE Redistribution Audit Report                        
┏━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Rule ID ┃ Severity ┃ Device ┃ Issue Description                                    ┃
┡━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ A1      │ High     │ R2     │ Process ospf 1 redistributes eigrp without route-map │
│ A3      │ High     │ R3     │ OSPF redistribution is missing 'subnets' keyword     │
│ A5      │ High     │ R3     │ OSPF external distance (110) < EIGRP external (170)  │
└─────────┴──────────┴────────┴──────────────────────────────────────────────────────┘
Status: FAIL (3 finding(s) detected)
```

---

## 🚀 How to Run the Project (Step-by-Step)

### Prerequisites
- Python 3.11, 3.12, or 3.14.
- Git.
- Optional: Docker & Docker Compose (for containerized deployment).
- Optional: Cisco IOS-XE routers or EVE-NG/GNS3 (for live lab mode).

---

### Mode 1: Instant 90-Second Demo (Zero Setup)

You can run the complete end-to-end simulator without needing any routers or lab networks. The packaged demo uses pre-recorded offline fixtures:

```bash
# 1. Activate your virtual environment
.venv\Scripts\activate       # Windows PowerShell
# source .venv/bin/activate  # Linux / macOS

# 2. Run the demo command
t2t demo
```

**What the demo executes automatically:**
1. Runs pre-flight checks against R1–R4.
2. Injects CCNP fault `T3` (distance inversion loop).
3. Prints the non-technical incident ticket.
4. Inspects routing table status across all 4 routers.
5. Requests a pedagogical Level 1 mentor hint.
6. Pushes the correct Cisco remediation (`distance ospf external 171`).
7. Evaluates the route oracle and anti-drift engine.
8. Displays the verified final scorecard.

---

### Mode 2: Full Offline Simulation (Replay Mode)

You can run an interactive, step-by-step troubleshooting session on your terminal:

```bash
# Step 1: Pre-flight doctor check
t2t doctor --replay

# Step 2: Start a new ticket with fault T3
t2t new-ticket --fault T3 --replay

# Step 3: Inspect the prefix status matrix
t2t status --replay

# Step 4: Request pedagogical mentor hints if you need guidance
t2t hint

# Step 5 (Optional): Reveal the reference solution commands if stuck
t2t reveal --replay -y

# Step 6 (Optional): Abandon active ticket and revert network to baseline
# Use this command whenever you want to forfeit or restart a failed ticket!
t2t abandon --replay -y

# Step 7: Submit your fix with an explanation for verification and scoring
t2t submit --replay -e "Restored distance ospf external 171 on R3 to prevent route feedback loop."

# Step 8: Review your session history and performance statistics
t2t history --stats
```

---

### Mode 3: Live Real-Time Web Dashboard & Topology API

The platform includes a built-in read-only web server powered by FastAPI and an interactive SVG topology visualizer.

#### 1. Starting the Web Dashboard
Launch the server in offline replay mode on port 8000:
```bash
# Launch dashboard locally in replay mode
t2t web --replay --port 8000
```

#### 2. Web UI Demonstration Steps (Browser Tour)
Open your browser to: **`http://127.0.0.1:8000`**

During a presentation or demonstration, walk through the 5 visual sections:
1. **Interactive SVG Topology:** Routers R1 (Branch), R2 (ASBR-1), R3 (ASBR-2), and R4 (HQ Core) with dynamic link interconnects.
2. **Real-Time Link Telemetry:** Link lines are dynamically color-coded:
   - 🟢 **Green:** Verified healthy paths.
   - 🟡 **Amber:** Suboptimal or asymmetric routing warning.
   - 🔴 **Red:** Down link, packet blackhole, or routing loop.
3. **Redistribution Prefix Matrix:** Live 4-router routing table status for key CCNP prefixes (`10.10.1.0/24`, `10.10.2.0/24`, `10.10.99.0/24`, `172.16.10.0/24`, `172.16.20.16/28`), showing protocol, AD, and next-hop IP.
4. **Active Incident Ticket Panel:** Real-time problem statement, symptom class, target ASBRs, and mentor hint counter.
5. **Session History Table:** Chronological log of past sessions, scores, and completion times.

#### 3. Interactive OpenAPI / Swagger Documentation
Navigate to **`http://127.0.0.1:8000/docs`** to demonstrate:
- Auto-generated OpenAPI schema.
- Interactive endpoint test console.
- **Strictly Read-Only Architecture:** Point out to evaluators that all endpoints are strictly `GET`-only (`/api/status`, `/api/session`, `/api/history`, `/api/audit/latest`), ensuring zero risk of unauthorized network configuration changes (AGENTS.md Rule 9).

#### 4. REST API Telemetry Commands (CLI Demonstration)
Demonstrate how NOC telemetry systems and external tools query the simulator:
```powershell
# 1. Query real-time redistribution prefix status across all 4 routers
curl http://127.0.0.1:8000/api/status

# 2. Query active ticket session details and hint levels
curl http://127.0.0.1:8000/api/session

# 3. Query candidate score history and timestamped logs
curl http://127.0.0.1:8000/api/history

# 4. Query latest AST configuration audit findings
curl http://127.0.0.1:8000/api/audit/latest
```

#### 5. Enterprise Security: Secure Remote Access & Token Authentication
By default, the server strictly refuses binding to `0.0.0.0` for safety. To allow remote access, you must specify both `--allow-remote` and a bearer token:
```bash
# Start server with remote access and bearer token
t2t web --host 0.0.0.0 --port 8000 --allow-remote --token "MySecureToken123" --replay
```
Access the protected API with the authorization header:
```bash
curl -H "Authorization: Bearer MySecureToken123" http://localhost:8000/api/status
```

---

### Mode 4: Running Production Audits

Audit any folder containing Cisco IOS-XE `.cfg` or `.txt` running configs:

```bash
# Audit the packaged baseline configs
t2t audit --from-dir src/t2t/demo_data/baseline --format table

# Audit with markdown report output
t2t audit --from-dir src/t2t/demo_data/baseline --format md --output audit_report.md

# Audit with JSON output validated against JSON Schema
t2t audit --from-dir src/t2t/demo_data/baseline --format json
```

---

### Mode 5: Live Hardware / EVE-NG / GNS3 Lab Mode

If you have real Cisco IOS-XE routers or an EVE-NG / CML / GNS3 lab:

1. **Configure credentials:**
   ```bash
   cp lab/inventory.example.yaml lab/inventory.yaml
   cp .env.example .env
   ```
2. **Edit `lab/inventory.yaml`** with the IP addresses of your routers (R1, R2, R3, R4).
3. **Render golden configuration templates:**
   ```bash
   python lab/scripts/render_golden.py
   ```
4. **Test live router connectivity:**
   ```bash
   t2t doctor
   ```
5. **Start a live troubleshooting session:**
   ```bash
   t2t new-ticket --fault T1
   ```
6. **Qualify a fault scenario across 3 consecutive cycles:**
   ```bash
   t2t qualify --fault T3 --runs 3
   ```

---

### Mode 6: Docker & Docker Compose Deployment

#### Running via Docker
```bash
# Build the multi-stage non-root Docker image
docker build -t t2t:latest .

# Run the 90-second demo in a clean container
docker run --rm -it t2t:latest demo
```

#### Running via Docker Compose
```bash
# Start t2t web dashboard service
docker compose --profile web up -d t2t-web

# Start local Ollama AI alongside t2t
docker compose --profile ai --profile web up -d
```

---

## 💻 CLI Command Reference

| Command | Flags / Options | Description |
|---|---|---|
| `t2t demo` | *None* | Runs the complete self-contained 90-second automated demo. |
| `t2t doctor` | `--replay` | Runs pre-flight diagnostics (SSH port 22, login, IOS-XE version, golden config). |
| `t2t new-ticket` | `--fault <T1..T10>`, `--level <1..3>`, `--replay` | Injects fault scenario and presents support ticket. |
| `t2t status` | `--replay` | Displays routing table matrix for all redistribution prefixes across all nodes. |
| `t2t hint` | *None* | Requests the next tiered hint (maximum 3 hints per session). |
| `t2t submit` | `-e, --explanation <TEXT>`, `--replay` | Verifies fix, evaluates configuration drift, and calculates score. |
| `t2t reveal` | `--replay`, `-y, --yes` | Reveals reference solution and restores baseline (forfeits score). |
| `t2t abandon` | `--replay`, `-y, --yes` | Cancels the active session and rolls back router configurations. |
| `t2t reset` | `--force`, `--replay` | Replaces running configs with golden baselines across all routers. |
| `t2t history` | `--limit <N>`, `--stats` | Shows log of completed sessions, average scores, and time records. |
| `t2t shell` | `--replay` | Launches an interactive troubleshooting REPL shell. |
| `t2t qualify` | `--fault <ID>`, `--all`, `--runs <N>` | Runs qualification harness to verify fault injection/revert cycle. |
| `t2t audit` | `--from-dir <DIR>`, `--format <table\|json\|md>`, `--output <PATH>`, `--fail-on <High\|Med\|Low>` | Audits Cisco configurations against rules A1–A7. |
| `t2t web` | `--host <IP>`, `--port <PORT>`, `--allow-remote`, `--token <TOKEN>`, `--replay` | Starts read-only FastAPI dashboard with real-time SVG topology. |

---

## 🔧 Configuration & Environment Variables

Create a `.env` file in the project root to configure local settings:

| Variable | Default Value | Description |
|---|---|---|
| `T2T_INVENTORY` | `lab/inventory.yaml` | Path to router inventory file. |
| `T2T_STATE_FILE` | `.t2t/state.json` | Path to session lock and active fault state file. |
| `T2T_DB_PATH` | `.t2t/t2t.db` | Path to SQLite database for sessions and metrics. |
| `T2T_AI_PROVIDER` | `none` | AI provider: `none`, `ollama`, `openai`, or `anthropic`. |
| `T2T_OLLAMA_URL` | `http://localhost:11434` | Ollama API endpoint. |
| `T2T_AI_MODEL` | `llama3:8b` | Model name for ticket/mentor generation. |
| `OPENAI_API_KEY` | `""` | API key if using OpenAI. |
| `ANTHROPIC_API_KEY` | `""` | API key if using Anthropic Claude. |
| `T2T_LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `T2T_WEB_TOKEN` | `""` | Secret bearer token for web dashboard remote access. |

---

## 🧪 Test Suite, Quality Gates & CI/CD

The project enforces comprehensive test coverage and linting standards:

```bash
# 1. Run all offline unit & contract tests (127 tests)
pytest

# 2. Run static type checking
mypy src

# 3. Run Ruff code quality linter
ruff check .

# 4. Check formatting
ruff format --check .

# 5. Build strict documentation site
mkdocs build --strict
```

All 127 automated tests run fully offline in under **8 seconds**, providing immediate feedback during development.

---

## 📜 License & Acknowledgments

- **License:** Released under the [MIT License](LICENSE).
- **Author:** Jeet Dhaduk.
- **Reference:** Cisco Press *CCNP and CCIE Enterprise Core ENCOR 350-401 Official Cert Guide* & *CCNP Enterprise Advanced Routing ENARSI 300-410 Official Cert Guide*.
