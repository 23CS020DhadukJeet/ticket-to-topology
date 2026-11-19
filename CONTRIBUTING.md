# Contributing to Ticket-to-Topology

Thank you for your interest in contributing to Ticket-to-Topology (`t2t`)!

---

## 1. Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/jeetdhaduk/ticket-to-topology.git
   cd ticket-to-topology
   ```
2. Create and activate a Python 3.11+ virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies in editable mode:
   ```bash
   pip install -e '.[dev]'
   ```

---

## 2. Coding Guidelines & Invariant Rules

Please adhere strictly to the project rules outlined in `AGENTS.md`:
- **Netmiko Import Rule:** Only `src/t2t/devices/netmiko_device.py` may import `netmiko`.
- **Fault Declarations:** Faults are strictly defined in `src/t2t/faults/catalog/*.yaml`. Never hard-code faults in Python.
- **Verification Independence:** `t2t.verify`, `t2t.faults`, `t2t.session.scoring`, and `t2t.audit` must never import `t2t.ai`.
- **Configuration Changes:** All device changes must go through `DeviceSession.push_config`. Audit sessions are read-only and never call `push_config`.
- **Secrets:** Never commit secrets or credentials. Use environment variables.
- **Clock Protocol:** Use the injectable `Clock` protocol (`FakeClock` / `SystemClock`). Do not use `time.sleep` in library code or tests.

---

## 3. Pre-Commit Verification

Before submitting changes, ensure all checks pass:
```bash
ruff check .
ruff format --check .
mypy src
pytest
```

---

## 4. Commit Message Convention

Follow standard Conventional Commits:
`type(scope): summary`

Examples:
- `feat(audit): implement A7 metric-type rule`
- `fix(parsers): handle subnetted route descriptor blocks`
- `test(session): add drift evaluation edge cases`
- `docs(runbook): add symptom recovery for sqlite lock`
