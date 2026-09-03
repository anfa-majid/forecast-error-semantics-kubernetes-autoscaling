# Step 14 — Frozen Final Experimental Protocol and Run Matrix

Version: 1.0.0  
Protocol ID: `anfa-final-experimental-protocol-v1`  
Status: **frozen before final operational outcomes**

## Completion statement

Step 14 converts the verified artifacts from Steps 7–13 into a deterministic, outcome-blind execution and analysis plan. The package contains 142 uniquely identified runs: 112 primary matched-error runs, 20 oracle reference runs, and 10 selected secondary safety-enabled runs.

## Research design

Seven Step 12 pairs are retained because each passed the preregistered MAE (<2%) and RMSE (<3%) matching tolerances, semantic gates, byte-exact regeneration, and outcome-blind validation. Each pair is evaluated only on its scientifically applicable workload. The primary controller safety net is disabled. Eight repetitions are assigned to each of the 14 matched forecast conditions. Oracle references receive five repetitions on each of the four workloads. The secondary safety analysis repeats persistent negative bias and missed peak five times with safety enabled.

The ordinary baseline forecast, reactive HPA, and stable/noisy control are excluded for explicit scope reasons recorded in the machine-readable protocol. Their exclusion is not based on Kubernetes outcomes.

## Final counts

| Component | Calculation | Runs |
|---|---:|---:|
| Primary matched comparisons | 7 pairs × 2 sides × 8 repetitions | 112 |
| Oracle references | 4 workloads × 5 repetitions | 20 |
| Secondary safety analysis | 2 critical conditions × 5 repetitions | 10 |
| **Total** | | **142** |

## Workload applicability

| Workload | Matched questions |
|---|---|
| gradual-ramp-v1 | stable-period versus transition-period error |
| narrow-spike-v1 | missed versus false peak; early versus late timing |
| sustained-peak-v1 | negative versus positive persistent bias; shortened versus extended peak |
| periodic-triangle-v1 | smoothed versus sharpened shape; early versus late timing |

## Randomization

The order is generated with seed `14001` in eight balanced repetition blocks. Blocks 1–5 contain matched conditions, four distributed oracle references, and two secondary safety runs. Blocks 6–8 contain matched conditions. Forecast sides are shuffled within every block, and identical workload/condition adjacency is avoided when possible. The generated sequence is immutable; deviations must be recorded, not silently reordered.

## Outcomes and analysis

The primary outcome is deficient ready-replica-seconds relative to the oracle. Secondary outcomes are excess ready-replica-seconds, SLO-violation seconds, P99 latency, failure rate, completion ratio, and scale-up lateness. Pair-specific effects are computed as side B minus side A within repetition block. The primary inference uses a two-sided exact paired permutation test where feasible, with a Wilcoxon signed-rank sensitivity analysis and a 95% bootstrap interval for the paired median. Holm correction controls the family-wise error rate across the seven primary pair tests.

The SLO remains frozen from Step 13: P99 ≤ 300 ms, failure rate <1%, and completion ratio ≥99%.

## Failed runs and exclusions

Only technical invalidity can exclude an attempt. High latency, SLO failure, capacity shortage, readiness delay, overprovisioning, and unexpected outcomes remain valid evidence. Every invalid attempt is retained with its reason. Its predefined matrix cell is rerun with an incremented attempt number; no outcome-based substitution is permitted.

## Runtime

Scheduled collection time is approximately 21.23 hours. Including the frozen T0 lead and inter-run stability allowance, planned cluster occupancy is approximately 27.15 hours before contingencies. A 15% operational contingency gives approximately 31.22 cluster-hours.

## Package contents

- `configuration/frozen-protocol.json`: authoritative rules.
- `matrix/condition-catalog.csv`: condition definitions and matched accuracy.
- `matrix/run-matrix.csv`: all preassigned experimental cells.
- `matrix/randomized-run-order.csv`: immutable execution sequence.
- `matrix/run-matrix.json`: machine-readable sequence.
- `analysis/statistical-analysis-plan.md`: estimands, tests, multiplicity, and missing-data rules.
- `analysis/runtime-estimate.csv`: duration and resource estimate.
- `validation/validation-summary.json`: automated completion checks.
- `manifests/SHA256SUMS.csv`: integrity ledger.

## Freeze rule

After this package is finalized, conditions, repetitions, outcomes, exclusions, and tests must not be added, removed, or changed in response to favorable or unfavorable final results. Any unavoidable operational amendment must be timestamped, justified without reference to outcomes, versioned, and preserved alongside this version.
