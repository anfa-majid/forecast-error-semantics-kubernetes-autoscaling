# Step 7 - Workload Trace Suite

Status: generated and automatically validated  
Suite version: `1.0.0`

## Executive result

Step 7 defines five deterministic workload traces for the final Azure K3s research environment: gradual ramp, narrow spike, sustained peak, periodic triangle wave, and stable/noisy control. The suite uses the Step 5 empirical capacity lookup `C1=30`, `C2=40`, `C3=55`, `C4=65 RPS` and the Step 6 forecast horizon `H=6 seconds`.

All primary traces remain at or below 60 RPS, retaining 5 RPS of headroom below the validated four-Pod limit. The 25 RPS baseline requires one Pod. The mandatory traces cross meaningful replica boundaries, while the optional control intentionally stays inside the one-Pod decision region.

## Frozen design

| Parameter | Value |
|---|---:|
| Sample interval | 1 second |
| Controller decision interval | 1 second |
| Forecast horizon | 6 seconds |
| Baseline | 25 RPS |
| Main peak | 60 RPS |
| Validated maximum | 65 RPS |
| Initial stable period | 60 seconds for mandatory traces |
| Suite version | 1.0.0 |

The one-second controller interval is frozen for the Step 7 workload/controller timing contract. A later change requires documented change control and regeneration of forecast and oracle schedules.

## Empirical oracle

The oracle uses the smallest validated Pod count whose empirical capacity covers workload:

`oracle_replicas(W) = min {N in {1,2,3,4} : W <= C_N}`

| Workload | Required Pods |
|---:|---:|
| 0-30 RPS | 1 |
| >30-40 RPS | 2 |
| >40-55 RPS | 3 |
| >55-65 RPS | 4 |

This lookup must not be replaced by `ceil(W/30)` because Step 5 found decreasing multi-Pod scaling efficiency.

## Trace catalogue

| Trace | Duration | Range | Scientific purpose |
|---|---:|---:|---|
| gradual-ramp-v1 | 480 s | 25-60 RPS | Early/late timing, slope error, readiness alignment, boundary mediation |
| narrow-spike-v1 | 180 s | 25-60 RPS | Missed/false peak, brief shortage, safety response timing |
| sustained-peak-v1 | 360 s | 25-60 RPS | Persistent bias, amplitude, duration, DRS/ERS asymmetry |
| periodic-triangle-v1 | 720 s | 25-60 RPS | Phase shift, repeated timing error, churn and repeated waste/deficit |
| stable-noisy-control-v1 | 240 s | 23-27 RPS | Stable-period control and errors that do not change decisions |

## File contract

Each file in `workloads/` contains one row per second with `trace_id`, `suite_version`, `offset_ms`, `target_rps`, `interpolation`, `phase`, `event_label`, and `oracle_replicas`.

Each file in `request-schedules/` is the exact deterministic expansion of its RPS trace into individual request dispatch offsets. Fractional per-second ramp rates use a cumulative remainder, and requests assigned to a second are evenly spaced at interval midpoints. This avoids random arrivals while keeping the cumulative scheduled count within one request of the mathematical trace integral.

Each file in `oracle/` gives both the demand-time requirement and the decision-time oracle target at `t+6 seconds`. Targets beyond the trace end use the final stable workload value and are explicitly marked `terminal_extension=true`.

Each annotation JSON records the equation, purpose, event list, detected replica-boundary crossings, duration, RPS range, and oracle replica range.

## Interpretation constraints

- These files define scheduled offered workload, not achieved throughput. Execution fidelity must be validated from load-generator dispatch logs.
- The exact per-request schedules are the authoritative dispatch plan. The load generator must consume these offsets directly or prove an identical expansion during a dry run.
- The traces are valid for the measured Azure K3s lookup and the benchmark configuration used in Steps 4-6.
- Loads above 65 RPS are outside the validated range.
- The stable/noisy control is optional and must not displace the four mandatory workloads if experiment time is constrained.
- Step 7 defines ground truth only. Accuracy-matched forecast mutations belong to the next experimental-design step.

## Completion assessment

| Written Step 7 requirement | Evidence | Status |
|---|---|---|
| Clear purpose for every workload | Trace catalogue and annotation `purpose` fields | Complete |
| Deterministic traces | Generator, workload CSVs, equations and checksums | Complete |
| Nonzero minimum and validated maximum | Automated range checks; 23-60 RPS within 65 RPS | Complete |
| Meaningful replica-boundary crossings | Detected crossing records and plots | Complete for mandatory traces |
| Practical durations | 180-720 seconds per trace | Complete |
| Stable, transition, peak and recovery annotations | Trace-specific event and phase records | Complete |
| Expected oracle replicas | Per-second workload files and oracle timelines | Complete |
| Saved request schedules | Exact per-request dispatch-offset CSVs | Complete |
| Equations/files, plots and justification | This report plus generated artifacts | Complete |
| Reproducibility | Versioned manifest, generator, independent validator and SHA-256 ledger | Complete |

All workloads have explicit purposes, deterministic equations, trace-specific phases, operational event annotations, expected oracle replicas, exact request schedules, practical durations, plots, hashes, and automated validation. Step 7 is complete at the workload-design and executable-trace level. Cluster execution of these workloads is an integration activity for the experiment runner and does not alter the frozen workload definitions.
