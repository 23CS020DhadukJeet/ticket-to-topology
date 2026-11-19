# Performance Benchmarks & CI Regression Thresholds

This document records baseline performance metrics for Ticket-to-Topology (`t2t`) operations in offline replay mode and defines regression thresholds enforced in CI.

## 1. Replay Mode Execution Benchmarks

In offline replay mode (`--replay`), network I/O is backed by frozen fixture files and `MockDevice` instances, eliminating network jitter and router convergence settle delays.

### Benchmark Measurements (x86_64 / Windows & Linux)

| CLI Command | Mode / Scenario | Mean Duration | P95 Duration | Max Duration | Exit Code |
|---|---|---|---|---|---|
| `t2t doctor --replay` | Mock offline health checks | 1.22 s | 1.35 s | 1.50 s | 0 |
| `t2t new-ticket --replay --fault T3 --no-ai` | Fault injection & state init | 1.28 s | 1.40 s | 1.55 s | 0 |
| `t2t status --replay` | Prefix routing table evaluation | 1.21 s | 1.30 s | 1.45 s | 0 |
| `t2t submit --replay -e "..."` | Check evaluation & score | 1.22 s | 1.35 s | 1.50 s | 0 / 1 |
| `t2t audit --from-dir <dir>` | 4 routers, 7 rule evaluations | 0.48 s | 0.65 s | 0.85 s | 0 / 1 |
| `t2t reset --replay` | Lab reset & baseline checks | 1.25 s | 1.38 s | 1.50 s | 0 |
| `t2t abandon --replay -y` | Session forfeit & reset | 1.24 s | 1.35 s | 1.45 s | 0 |

*Note: In CLI mode, Python startup and Typer/Rich module import account for ~0.9s of total command invocation time; actual core domain execution inside `SessionService` and `AuditService` is < 0.05s.*

---

## 2. CI Regression Thresholds

To prevent performance regressions in continuous integration, replay operations must not exceed the following hard gates:

| Component / Workflow | CI Threshold Gate | Rationale |
|---|---|---|
| Full Unit Test Suite (`pytest`) | $\le 15.0\text{ s}$ | Currently executes 118+ tests in ~7.5s. |
| Single Command Replay (`doctor`, `audit`) | $\le 3.0\text{ s}$ | Guarantees instant feedback in CI and offline developer use. |
| Offline Audit Evaluation (`AuditService`) | $\le 1.0\text{ s}$ | In-memory AST/model parsing of 4 router configs. |
| Fault Reset / State Settle (`replay=True`) | $\le 0.1\text{ s}$ | Uses `FakeClock` with zero real sleeping. |
| Test Coverage | $\ge 85\%$ | Enforced on parsers, verify, faults, audit, and session modules (currently 91%). |

---

## 3. Live Lab Timing vs. Replay Mode

On live hardware (Cisco IOS-XE on C8000v / CSR1000v), network and convergence delays govern timing:

- **EIGRP Convergence:** ~2–5 seconds after topology or metric changes.
- **OSPF SPF & LSA Flooding:** ~5–10 seconds for full redistribution convergence across dual ASBRs.
- **Config Replacement (`configure replace`):** ~15–30 seconds for IOS-XE rollback archive commit.
- **Settle Windows:** The harness uses dynamic adaptive polling via `t2t.faults.settle.wait_for_settle` with a default timeout of 30 seconds rather than hard-coded `time.sleep` calls.
