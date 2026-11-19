# Operational Runbook: Symptom $\rightarrow$ Recovery Guide

This runbook documents common operational faults, environment anomalies, error codes, and standard recovery procedures for Ticket-to-Topology (`t2t`).

---

## 1. Quick Troubleshooting Matrix (Appendix C)

| Symptom | Likely Cause | Recovery Procedure |
|---|---|---|
| `doctor` FAIL: login | RSA key missing / wrong password / `.env` stale | On router console: `crypto key generate rsa modulus 2048`; re-render golden template; verify `LAB_USERNAME` and `LAB_PASSWORD` in `.env`. |
| `configure replace` fails or hangs | Missing `archive` block, wrong `golden_path`, or image quirk | Verify `golden_path` (default `flash:golden.cfg`); ensure `archive` config exists; fall back to fault `revert` commands or restore simulator snapshot `lab-baseline-v1.0`. |
| `new-ticket` says "another fault active" | Stale active session in `.t2t/state.json` or `.t2t/t2t.db` | Run `t2t reset --force` or `t2t abandon -y` to clear active state and restore baseline. |
| Baseline never converges | Interface down / link flapped / simulator CPU starved | Check `show ip eigrp neighbors` and `show ip ospf neighbor`; restart stuck simulator node; revert to clean snapshot `lab-baseline-v1.0`. |
| `FixtureMissing` in replay mode | Missing recorded output for requested show command | Run `python lab/scripts/capture_fixtures.py` on live lab to capture missing commands to `tests/fixtures/baseline/`. |
| LLM timeout or 503 error | Local Ollama overloaded / remote Gemini/OpenAI rate limit or bad key | Increase `T2T_AI_TIMEOUT` (e.g. 45.0), pass `--no-ai`, or set `T2T_AI_PROVIDER=none`. The system automatically falls back to deterministic templates. |
| SQLite "database is locked" | Concurrent access by multiple `t2t` CLI sessions or dangling transaction | Terminate other running `t2t` processes or background shells; remove stale `.t2t/state.lock` if process terminated abruptly. |
| Windows: garbled colours/paths | Terminal encoding or non-UTF8 code page | Use Windows Terminal; launch with `PYTHONUTF8=1`; set `NO_COLOR=1` if ANSI escape codes fail to render. |

---

## 2. Typed Error Hierarchy & Exit Codes (Phase 8)

Every non-zero exit code in `t2t` is stable and documented:

| Exit Code | Exception Class | Description & Remediation |
|---|---|---|
| **0** | Success | Command completed successfully with no critical errors or findings. |
| **1** | Generic / Verification Failure | Verification checks failed during `submit`, or general command execution error. |
| **2** | Audit Finding / Connectivity | In `t2t audit`: findings detected at or above `--fail-on` threshold, or config path missing. |
| **10** | `DeviceUnreachable` | Router SSH/TCP port 22 timed out or connection dropped after 3 retries. Check router power, hypervisor interfaces, and management IP routing. |
| **11** | `AuthFailed` | Authentication rejected by router AAA/TACACS+/local database. Confirm credentials match `.env`. |
| **12** | `FixtureMissing` | Offline replay requested a show command not recorded in `tests/fixtures/`. Run `capture_fixtures.py` or check `MockDevice` scenario. |
| **13** | `FaultInvalid` | Catalog YAML file has invalid syntax, missing counterpart revert rules, or unknown routers. Validate YAML against `FaultModel` schema. |
| **14** | `AIUnavailable` | Configured AI provider timed out, returned 5xx, or failed authentication. Enable deterministic fallback with `--no-ai`. |
| **15** | `StateCorrupt` | Active state JSON or SQLite store could not be parsed or acquired lock. Run `t2t reset --force`. |
| **16** | `ReadOnlyViolation` | A non-show command or configuration push was attempted on a read-only device session (such as `t2t audit` or `t2t doctor`). |

---

## 3. Global Debug Flag (`--debug`)

By default, `t2t` prints clean, user-friendly error messages without technical Python tracebacks:

```bash
$ t2t new-ticket --fault T3
Error: Router R2 connection timed out
```

To view the full Python stack trace and exception chain for diagnostics, pass the global `--debug` flag before the subcommand:

```bash
$ t2t --debug new-ticket --fault T3
Traceback (most recent call last):
  File "src/t2t/cli/app.py", line 180, in new_ticket
    ...
t2t.errors.DeviceUnreachable: Router R2 connection timed out
```

---

## 4. Log Inspection & Correlation IDs

Logs are written to `logs/t2t.log` with automatic rotation (`RotatingFileHandler` with 10 MB per file and 5 backups). Sensitive secrets (API keys, router passwords) are automatically masked as `***`.

Each troubleshooting session assigns a unique correlation ID formatted as `[SES-<id>]` (or `[soak-<n>]` during soak runs):

```text
2026-11-17 18:08:33,123 [INFO] [SES-12345] t2t.session.service: Starting ticket for fault T3 (level 2)
2026-11-17 18:08:34,456 [INFO] [SES-12345] t2t.devices.session: Pushing 1 config commands to R3
```

To filter logs for a specific session:
```bash
# On Linux / macOS
grep "\[SES-12345\]" logs/t2t.log

# On Windows PowerShell
Select-String "\[SES-12345\]" logs/t2t.log
```

---

## 5. Lab Reset & Recovery Procedures

### Clean Reset to Baseline
```bash
t2t reset
```

### Force Reset (Clears Stale Fault State & Lock Files)
```bash
t2t reset --force
```

### Manual Router Snapshot Recovery (EVE-NG / CML / GNS3)
If a router's running configuration diverges beyond automated recovery:
1. Stop nodes in the hypervisor topology.
2. Revert nodes to snapshot `lab-baseline-v1.0`.
3. Start nodes and wait 60 seconds for OSPF and EIGRP adjacencies to form.
4. Run `t2t doctor` to confirm full environment health.
