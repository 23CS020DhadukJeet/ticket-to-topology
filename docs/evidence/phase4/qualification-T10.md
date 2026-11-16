# Qualification Report: T10 — Wrong interface in connected-redistribution route-map on R1

- **Status:** **QUALIFIED (PASS)**
- **Total Duration:** 0.09s
- **Generated At:** `2026-11-16T21:17:26.995946+00:00`
- **Observed Symptom:** Qualified symptom observed

## Qualification Runs

| Run | Baseline Pre | Fault Checks Pre | Injected Failing Checks | Revert Pass | Baseline Post | Duration | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | True | True | `c_t10_r2_route, c_t10_r4_route` | True | True | 0.03s | **PASS** |
| 2 | True | True | `c_t10_r2_route, c_t10_r4_route` | True | True | 0.03s | **PASS** |
| 3 | True | True | `c_t10_r2_route, c_t10_r4_route` | True | True | 0.03s | **PASS** |
