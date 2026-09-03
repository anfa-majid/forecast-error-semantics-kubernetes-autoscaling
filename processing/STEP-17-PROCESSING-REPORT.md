# Step 17 — Raw Data Processing Report

## Result

Step 17 processing produced a valid analysis-ready dataset from every accepted Step 15 and Step 16 attempt. The population is fixed at 142 unique runs: 132 safety-off runs from Step 15 and 10 safety-on runs from Step 16.

## Outputs

| Table | Rows | Primary key |
|---|---:|---|
| Aligned timeline | 59,400 | (`run_id`, `second`) |
| Run level | 142 | `run_id` |
| Event level | 290 | (`run_id`, `event_index`) |

The event count is independently explained by the workload design: 21 gradual-ramp events, 42 narrow-spike events, 185 periodic-triangle events (five per run), and 42 sustained-peak events.

## Processing approach

All sources are aligned to one-second bins relative to workload T0. Forecast values are aligned at their six-second-ahead target, not their issue time. Raw requests remain the authority for run/event P99 and request failures. Controller commands are compared with frozen oracle-policy commands. Desired and Ready replicas remain distinct.

Step 15 Ready replicas and Pod events use Kubernetes snapshots. Step 16 Ready replicas use live Deployment reads recorded in each safety decision. Step 16 Pod events are unavailable because its remote Kubernetes snapshot collector recorded `kubectl` execution errors; missing fields are preserved rather than imputed.

## Validation

All automated checks passed:

- 142 unique run keys and the expected 132/10 source split;
- 59,400 unique timeline keys;
- 290 unique event keys;
- all 20 oracle runs have zero MAE, RMSE, and desired-replica MAE;
- all 13 missed-peak events have a documented missing predicted onset;
- Step 15 and Step 16 readiness/Pod-event provenance is separated correctly;
- no Step 16 Pod event was zero-imputed.

Four runs were independently recomputed from the aligned timeline:

| Run | MAE | RMSE | SLO seconds | Deficient replica-s |
|---|---:|---:|---:|---:|
| `final-oracle-sustain-r01-s0` | 0 | 0 | 28 | 0 |
| `final-p03-b-r01-s0` | 6.034483 | 14.532959 | 66 | 180 |
| `final-p01-a-r01-s1` | 5 | 5 | 29 | 7 |
| `final-p03-b-r01-s1` | 6.034483 | 14.532959 | 19 | 21 |

Each recomputation matched the automated run-level row exactly within floating-point tolerance.

## Interpretation constraints

This step processes data; it does not test hypotheses or select favorable outcomes. One-second completion ratios can be sensitive to requests crossing bin boundaries, so request-level aggregate metrics are included alongside per-second SLO metrics. Requested replica-seconds are controller decisions, whereas Ready deficits use observed Ready state. These measures must not be substituted for each other.

## Completion assessment

- Raw data preserved: complete.
- Deterministic alignment and processing: complete.
- Transparent formulas: complete in `DATA-DICTIONARY.md`.
- Run-level table: complete.
- Event-level table: complete.
- Missingness documented: complete.
- Manual validation examples: complete.
