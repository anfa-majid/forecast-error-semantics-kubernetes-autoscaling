# Evidence Ledger 02 - Forecast-Error Duration

## Controlled contrast

- Contrast: shortened peak minus extended peak.
- Workload: `sustained-peak-v1`.
- Inferential unit: matched run repetition.
- Sample: 8 matched pairs (16 Step 15 runs).
- Aggregate-accuracy control: MAE = 2.9661 RPS and RMSE = 10.1889 RPS for both forecasts in every repetition.
- Estimand: B minus A, where A is extended peak and B is shortened peak.
- Important non-matching metric: transition MAE was 17.5 RPS for extended and 0 for shortened. Therefore this pair establishes equality of aggregate MAE/RMSE, not equality of transition-sensitive error.

## Evidence

| Outcome | Extended (A) | Shortened (B) | Paired effect B-A | 95% paired bootstrap CI | Raw exact p | Holm p | Pair direction |
|---|---:|---:|---:|---:|---:|---:|---|
| Desired-replica MAE | 0.25 | 0.25 | 0 | [0, 0] | 1 | 1 | 8 ties |
| Deficient replica-seconds | 0 | 90 | +90 | [90, 90] | 0.0078125 | 0.1640625 | 8 positive |
| Request P99 latency | 35.04 ms | 1578.83 ms | +1543.79 ms | [1269.02, 1866.57] | 0.0078125 | 0.1640625 | 8 positive |
| Composite-SLO duration | 21 s | 27 s | +6 s | [0.25, 11.5] | 0.1015625 | 1 | 5 positive, 3 negative |
| Excess replica-seconds | 90 | 0 | -90 | [-90, -90] | 0.0078125 | 0.0546875 | 8 negative |

## Causal interpretation

The forecasts have identical aggregate MAE and RMSE and equal absolute desired-replica error, but the decision error occurs on opposite sides of the workload event. The shortened forecast ends the peak before actual demand falls, causing a premature scale-down and 90 deficient replica-seconds. The extended forecast keeps the peak after actual demand falls, causing 90 excess replica-seconds without deficiency. The error duration/direction relative to the falling transition therefore determines whether equal decision-error magnitude becomes reliability harm or resource cost.

The large P99 difference is consistent with the readiness/capacity mechanism: premature scale-down overlaps continuing high demand, whereas late scale-down occurs after demand has already declined.

## SLO robustness

Across latency thresholds of 200, 300, and 500 ms:

- composite-SLO mean differences remained positive at +6.125, +6.0, and +5.875 seconds;
- all leave-one-pair-out mean estimates remained positive;
- composite pair-level directions were heterogeneous (5 positive, 3 negative);
- latency-only differences were +9.375, +9.25, and +8.25 seconds, with all 8 pairs positive and raw exact p = 0.0078125.

Thus the average harm direction is robust, but universal pair-level dominance is not supported under the composite SLO. The composite definition includes completion and failure effects that can add run-level variability even when tail-latency harm is strongly consistent.

## Safety evidence

No safety-on/off ablation was run for the shortened/extended pair. Step 20 must report the safety effect as not tested, not infer it from missed peaks or persistent bias.

## Negative and constraining findings

1. Desired-replica MAE was identical (0.25) despite opposite operational consequences. This demonstrates that absolute decision-error magnitude also loses direction and timing information.
2. Composite-SLO duration was not consistently larger in every shortened run: 5 pairs were positive and 3 negative; raw exact p = 0.1015625.
3. Transition MAE was not matched. It distinguishes the pair, so this comparison does not show that every forecast metric fails; a transition-sensitive metric captures part of the structural difference.
4. After Holm correction, neither harm nor cost outcome crossed 0.05. The effects should be reported with magnitudes, intervals, and direction counts rather than a multiplicity-adjusted significance claim.

## Defensible claim

For the tested sustained-peak workload, shortening versus extending a forecast peak while holding aggregate MAE and RMSE equal caused equal-magnitude replica-decision error to produce opposite consequences. Premature termination created 90 deficient replica-seconds and substantially higher request P99, whereas delayed termination created 90 excess replica-seconds. The shortened condition was worse on average for composite-SLO duration, but that SLO effect was heterogeneous across matched runs. Transition MAE distinguished the forecasts and is therefore informative for this error structure.

## Prohibited overclaims

- Do not say shortened peaks increased composite-SLO duration in every run.
- Do not claim transition MAE was held constant.
- Do not claim safety corrects duration errors; it was not tested for this pair.
- Do not describe Holm-adjusted results as significant at 0.05.
- Do not generalize the exact 90-replica-second exchange beyond this workload duration and controller policy.
