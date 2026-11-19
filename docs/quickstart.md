# Quick Start Guide

Get up and running with `t2t` in under 5 minutes.

---

## 1. Installation

### From Source (Editable Mode)
```bash
git clone https://github.com/jeetdhaduk/ticket-to-topology.git
cd ticket-to-topology
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e '.[dev]'
```

### Docker
```bash
docker run --rm -it ghcr.io/jeetdhaduk/ticket-to-topology:latest demo
```

---

## 2. Instant Demo (No Routers Required)

Run the self-contained scripted demonstration:
```bash
t2t demo
```
This command performs pre-flight checks, injects a simulated fault, inspects routing status, requests a mentor hint, applies remediation commands, and computes the final scorecard using offline fixtures.

---

## 3. Basic Troubleshooting Workflow

```bash
# 1. Verify lab health
t2t doctor --replay

# 2. Start a new troubleshooting ticket (e.g. Level 2 fault)
t2t new-ticket --fault T3 --replay

# 3. View routing table across key prefixes
t2t status --replay

# 4. Request a tiered pedagogical hint
t2t hint --replay

# 5. Submit your fix for technical verification
t2t submit --replay --explanation "Restored OSPF external distance 171 on R3 to prevent suboptimal routing."

# 6. View historical sessions
t2t history --stats
```

---

## 4. Running a Configuration Audit

Audit configurations offline from saved router config files:
```bash
t2t audit --from-dir tests/synthetic/audit/baseline --format table
```
Or export the audit findings report as JSON or Markdown:
```bash
t2t audit --from-dir tests/synthetic/audit/baseline --format json --output reports/
```
