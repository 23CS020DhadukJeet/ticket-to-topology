# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-17

### Added
- **Packaging & Demo (Phase 9):**
  - Standalone `t2t demo` command powered by self-contained fixture data in `src/t2t/demo_data/`.
  - Non-root multi-stage `Dockerfile` and `docker-compose.yml` with `/data` volume ownership fix.
  - Automated release pipeline in `.github/workflows/release.yml` with GHCR and GitHub Pages publishing.
  - MkDocs Material documentation site.
- **Hardening & Stability (Phase 8):**
  - Typed exceptions with stable exit codes (`DeviceUnreachable`, `AuthFailed`, `FixtureMissing`, `FaultInvalid`, `AIUnavailable`, `StateCorrupt`, `ReadOnlyViolation`).
  - Global `--debug` flag for detailed tracebacks; user-friendly clean errors by default.
  - Session correlation tracking and log rotation with `RotatingFileHandler`.
  - Redaction filter masking passwords, Bearer tokens, OpenAI (`sk-...`), and Gemini (`AIzaSy...`) API keys.
  - Comprehensive chaos test suite and overnight soak testing harness (`lab/scripts/soak.py`).
  - Enforced `--strict-host-keys` checking option.
- **Audit Engine (Phase 7):**
  - Static & live redistribution risk audit engine (`t2t audit`) implementing rules A1–A7.
  - Support for `--from-dir`, `--format` (table, json, md), `--output`, and `--fail-on`.
  - Formal JSON Schema validation for audit reports.
- **Learner Experience & Session Management (Phase 6):**
  - SQLite persistent session store with schema migrations and file locking.
  - CLI commands: `new-ticket`, `status`, `hint`, `submit`, `reveal`, `abandon`, `reset`, `history`, `shell`.
  - Pure scoring function computing deterministic results.
  - Section-level configuration drift detection.
- **AI Tutoring Layer (Phase 5):**
  - `LLMProvider` protocol with implementations for Ollama, Gemini, OpenAI, and None (offline).
  - Jargon guardrails on ticket generator and solution leak guards on mentor hints.
- **Fault Catalog & Engine (Phase 4):**
  - 10 validated redistribution fault scenarios (T1–T10) across Levels 1–5.
  - Adaptive protocol convergence settle loop (`wait_for_settle`).
- **Parsers & Verification Oracle (Phase 3):**
  - Parsers for Cisco IOS-XE route details, route-maps, and routing neighbors.
  - Verification engine for route attributes, next-hops, and ping reachability.
- **Device Abstraction Layer (Phase 2):**
  - Isolated `NetmikoDevice` with retries, timeouts, and read-only safety checks.
  - `MockDevice` and `DeviceSession` for deterministic offline replay.
