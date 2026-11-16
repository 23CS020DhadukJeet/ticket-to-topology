# AGENTS.md: rules for AI coding assistants

Project: ticket-to-topology (package t2t). Build manual: docs/BUILD_GUIDE.md.
Read only the section for the current phase plus this file.

## Hard rules
1. Only src/t2t/devices/netmiko_device.py may import netmiko.
2. Faults are YAML in src/t2t/faults/catalog. Never hard-code a fault in Python.
3. PASS or FAIL is decided only by t2t.verify. t2t.verify, t2t.faults and
   t2t.session.scoring must never import t2t.ai.
4. All device configuration changes go through DeviceSession.push_config.
   Audit code uses read_only devices and never calls push_config.
5. Never invent router output. tests/fixtures is captured from real routers; do
   not create or edit files there. If you need a fixture, tell me which command
   to capture. Synthetic test data lives only in tests/synthetic and is never
   used for a phase gate.
6. Never print, log or commit secrets. Credentials come from environment
   variables. Redact before sending any text to an LLM.
7. Write the test first and show it failing. Never weaken, skip or delete an
   existing test to make it pass.
8. Every network or LLM call has an explicit timeout.
9. Use yaml.safe_load. No eval/exec. No shell=True.
10. No time.sleep in library code or tests: use the injectable Clock.
11. Touch only the files named in the task. No extra features.

## Workflow
- One component per change. After each change run:
  ruff check . && ruff format . && mypy src && pytest
- Keep functions small and typed. Public functions have docstrings.
- If a requirement is unclear or router behaviour is uncertain, ask instead of
  guessing.
- Commit messages: type(scope): summary, e.g. feat(parsers): parse route detail.

## Commands
- Install: pip install -e '.[dev]'
- Offline tests: pytest            (lab tests excluded by default)
- Live-lab tests: pytest -m lab
- Qualify a fault: t2t qualify --fault T3 --runs 3
