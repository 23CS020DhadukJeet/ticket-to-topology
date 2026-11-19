# Architecture & Design Principles

Ticket-to-Topology is engineered around strict architectural boundaries to guarantee safety, determinism, and testability.

---

## 1. Hard Architectural Invariants

As enforced in `AGENTS.md` and verified by architecture tests (`test_no_ai_in_verify.py`):
1. **Netmiko Isolation:** Only `src/t2t/devices/netmiko_device.py` directly imports Netmiko. All higher-level services interact via the `DeviceSession` abstraction.
2. **Deterministic Verification:** PASS or FAIL decisions are strictly computed by `t2t.verify`. The AI modules (`t2t.ai`) are never imported by verification, fault injection, scoring, or audit engines.
3. **Configuration Gate:** Device configuration mutations can only proceed through `DeviceSession.push_config`. Read-only devices reject configuration commands before touching the network.
4. **Offline Replay Mode:** `MockDevice` allows every CLI command, audit rule, and troubleshooting ticket to run against recorded fixture files with identical behavioral semantics.
5. **Injectable Clock:** Network polling, retry backoff, and settle windows use the injectable `Clock` protocol (`FakeClock` / `SystemClock`), avoiding `time.sleep` calls in test suites.

---

## 2. Core Subsystems

```
┌─────────────────────────────────────────────────────────────┐
│                       CLI Layer (Typer)                     │
│  t2t doctor | new-ticket | hint | submit | audit | demo     │
└───────────────┬─────────────────────────────┬───────────────┘
                │                             │
    ┌───────────▼────────────┐    ┌───────────▼────────────┐
    │     Session Service    │    │     Audit Service      │
    │  State Machine & Store │    │ Rules Engine (A1 - A7) │
    └─────┬────────────┬─────┘    └───────────┬────────────┘
          │            │                      │
┌─────────▼──────┐  ┌──▼─────────────┐        │
│ AI Layer (LLM) │  │ Verify Engine  │        │
│ Ticket, Mentor │  │ Route, Ping    │        │
└────────────────┘  └──┬─────────────┘        │
                       │                      │
              ┌────────▼──────────────────────▼────────┐
              │             Device Session             │
              │  NetmikoDevice (SSH) | MockDevice (FS) │
              └────────────────────────────────────────┘
```

- **`t2t.devices`:** Abstraction layer for real SSH connections (`NetmikoDevice`) or offline fixture playback (`MockDevice`).
- **`t2t.parsers`:** Parsing Cisco IOS-XE outputs (`show ip route`, `show ip protocols`, `show ip eigrp neighbors`, `show ip ospf neighbor`, `show route-map`, `show running-config`).
- **`t2t.faults`:** YAML-based catalog loader, inject/revert runner, and convergence settle verifier.
- **`t2t.verify`:** Technical pass/fail oracle evaluating route attributes, prefix reachability, next hops, and protocol adjacency.
- **`t2t.session`:** SQLite session store, state machine (`IDLE` $\leftrightarrow$ `ACTIVE`), drift detector, and scoring engine.
- **`t2t.ai`:** AI integrations (Gemini, OpenAI, Ollama) for incident generation, hints, and explanation grading with deterministic offline fallbacks.
- **`t2t.audit`:** Config parsing into structured `DeviceModel`s, evaluating pure rule functions A1–A7, and report writers (table, JSON, Markdown).
