# Step 5 local pilot findings — 2026-08-01

## Status

Pilot complete. These values locate the confirmatory boundary and do not freeze
`C_pod`.

The first broad run was interrupted by evidence-runner handling of an expected
nonzero overload exit and invalid combined kubectl resource syntax. Results for
25, 50, and 75 RPS were preserved. The runner was corrected, syntax-checked, and
the missing 100, 125, and 150 RPS points were executed in a separate run.

Before fine profiling, the unrelated Step 3 `worker-only-test` Deployment was
scaled to zero to remove background worker CPU demand. This is the declared
confirmatory baseline.

## Broad result

- 25 and 50 RPS: no failures, low tail latency, negligible throttling.
- 75 RPS with Step 3 test Pods active: P99 135.075 ms but 100% measured throttling.
- 100 RPS: 36.92% failures, 63.08 successful RPS, P99 9.895 seconds.
- 125 RPS: 70.60% failures, 36.75 successful RPS, P99 9.973 seconds.
- 150 RPS: 81.66% failures, 27.52 successful RPS, P99 9.962 seconds.

The high-load latency approaches the fixed 10-second client timeout and achieved
throughput diverges sharply from offered load.

## Fine boundary result

| Offered RPS | Errors | Mean ms | P50 ms | P95 ms | P99 ms | CPU cores | Throttling | Pilot pass |
|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 55 | 0 | 10.33 | 8.90 | 12.75 | 52.12 | 0.317 | 2.05% | yes |
| 60 | 0 | 8.90 | 8.74 | 10.63 | 12.52 | 0.331 | 2.46% | yes |
| 65 | 0 | 8.80 | 8.55 | 10.46 | 13.30 | 0.309 | 6.69% | yes |
| 70 | 0 | 9.86 | 8.62 | 15.11 | 37.50 | 0.399 | 27.84% | no |
| 75 | 0 | 12.25 | 9.03 | 34.11 | 56.67 | 0.341 | 65.00% | no |
| 80 | 0 | 658.98 | 210.72 | 2044.34 | 3382.48 | 0.357 | 100.00% | no |
| 85 | 0 | 1039.26 | 706.94 | 2713.29 | 3808.28 | 0.393 | 100.00% | no |
| 90 | 0 | 2789.63 | 2879.26 | 5087.44 | 5741.59 | 0.350 | 100.00% | no |

The provisional first failing condition is CPU throttling, at 70 RPS. Request
latency remains below the 300 ms SLO at 70 and 75 RPS, but the conservative
throttling guardrail prevents treating those rates as safe. At 80 RPS the latency
SLO also fails decisively.

## Confirmatory selection

Confirm 55, 60, 65, 70, and 75 RPS for five repetitions. Each point has a
30-second excluded warm-up, a 120-second measurement window, and 60-second
recovery. Point order rotates between repetitions. The highest monotonic load
that passes every repetition will become `C_pod_observed`, subject to the
pre-registered variability/safety-margin rule.

## Confirmatory checkpoint — repetition 1

The first 120-second confirmatory repetition completed with 30-second excluded
point warm-ups and 60-second recovery periods. All client, Kubernetes, CPU, and
throttling evidence files were present.

| Offered RPS | Completed | Errors | Mean ms | P50 ms | P95 ms | P99 ms | CPU cores | Throttling | Result |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 55 | 6,600 | 0 | 8.76 | 8.62 | 10.30 | 11.51 | 0.336 | 0.38% | pass |
| 60 | 7,200 | 0 | 9.10 | 8.91 | 10.87 | 13.25 | 0.353 | 3.79% | pass |
| 65 | 7,800 | 0 | 8.94 | 8.58 | 10.87 | 17.37 | 0.402 | 11.27% | fail: throttling |
| 70 | 8,400 | 0 | 9.83 | 8.60 | 13.18 | 42.24 | 0.437 | 25.71% | fail: throttling |
| 75 | 9,000 | 0 | 27.64 | 9.11 | 135.06 | 246.19 | 0.457 | 83.32% | fail: CPU and throttling |

The current repeated-evidence candidate is 60 RPS, but it is not frozen. Four
rotated confirmatory repetitions remain. A final `C_pod` requires every required
repetition at the selected point and all lower confirmatory points to pass.

## Five-repetition aggregate checkpoint

All five rotated repetitions completed, but the monotonic rule prevents freezing
60 RPS immediately:

| Offered RPS | Passing runs | Maximum P99 | Maximum throttling | All pass |
|---:|---:|---:|---:|:---:|
| 55 | 4/5 | 29.74 ms | 10.41% | no |
| 60 | 5/5 | 14.94 ms | 7.33% | yes |
| 65 | 0/5 | 140.59 ms | 12.30% | no |
| 70 | 0/5 | 175.02 ms | 94.72% | no |
| 75 | 0/5 | 5027.77 ms | 99.22% | no |

The isolated 55-RPS failure is a marginal throttling-guardrail failure, not a
latency, failure-rate, or throughput failure. It cannot be discarded selectively.
Five additional 50-RPS confirmatory repetitions are therefore required. If all
pass, 50 RPS will be the conservative monotonic `C_pod` candidate; otherwise the
boundary must move lower.

## Lower-bound checkpoint — 50 RPS

The 50-RPS condition completed 6,000/6,000 requests without errors in each of
five repetitions. P99 remained between 11.42 and 45.87 ms and mean CPU stayed
between 0.284 and 0.367 cores. However, repetition 2 measured 11.02% CPU
throttling, narrowly exceeding the strict `<10%` guardrail. Result: 4/5 pass.

The guardrail is retained as pre-registered. The next candidate is 45 RPS, tested
for five repetitions using the same warm-up, measurement, recovery, and evidence
procedure.

## Final local single-Pod capacity

All five 45-RPS repetitions passed every condition:

| Repetition | Completed | Errors | P99 | CPU cores | Throttling |
|---:|---:|---:|---:|---:|---:|
| 1 | 5,400 | 0 | 17.72 ms | 0.285 | 1.81% |
| 2 | 5,400 | 0 | 15.82 ms | 0.308 | 1.42% |
| 3 | 5,400 | 0 | 30.26 ms | 0.322 | 6.43% |
| 4 | 5,400 | 0 | 12.73 ms | 0.280 | 0.00% |
| 5 | 5,400 | 0 | 12.60 ms | 0.282 | 0.00% |

The local-development safe capacity is therefore frozen as:

`C_pod = 45 RPS`

This is the highest tested 5-RPS load below the non-monotonic marginal failures
at 50 and 55 RPS that passed all repetitions. It is intentionally conservative
and applies only to the recorded local kind/Docker Desktop configuration.
