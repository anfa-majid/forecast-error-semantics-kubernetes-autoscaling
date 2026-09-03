# Failed-Run and Exclusion Policy

1. Validate identity, clocks, reset, collectors, workload accounting, and evidence completeness without using outcome favorability.
2. If valid, retain the run even when latency, failures, capacity deficiency, or readiness behavior is extreme.
3. If technically invalid, preserve the complete attempt directory and assign a controlled reason code.
4. Rerun the same preassigned `run_id` cell with `attempt` incremented; retain both attempts.
5. Never replace a failed cell with another condition, never silently reorder completed evidence, and never stop a condition because its results appear favorable or unfavorable.
6. Any protocol amendment requires a new version, timestamp, rationale independent of outcomes, and an amendment ledger entry.
