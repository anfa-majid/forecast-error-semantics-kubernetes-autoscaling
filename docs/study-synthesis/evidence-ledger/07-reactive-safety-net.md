# Evidence Ledger 07 - Reactive Safety-Net Research Question

## Research question

How does a fixed reactive safety mechanism change the operational impact of different forecast-error structures?

## Controlled design

- Directly tested errors: persistent negative bias (`sustained-peak-v1`) and missed peak (`narrow-spike-v1`).
- Comparison: identical workload and forecast replayed safety off versus safety on.
- Inferential unit: matched run repetition.
- Sample: 5 matched pairs per error (20 runs across off/on comparators).
- Forecast MAE, RMSE, and transition MAE are exactly unchanged by safety.
- Step 16 controller: v1.1.1. Step 19 persistence robustness replacements used reliability-amended v1.1.2 and were analyzed as a separate block, not pooled.

## Fixed mechanism

1. Observe finalized dispatched requests in one-second windows.
2. Estimate Ready capacity with the fixed 1->30, 2->40, 3->55, 4->65 RPS lookup.
3. Mark overload when observed demand exceeds estimated Ready capacity.
4. Trigger after two consecutive overload windows.
5. Raise the safety floor to the minimum replicas required by observed demand.
6. Issue `max(predictive command, safety floor)` through a single arbiter/writer.
7. Release after protection need clears and a fixed 30-second hold expires.
8. Missing observations are logged and never inferred as overload.

The rule, thresholds, capacity lookup, and release behavior were identical across both tested error types.

## Persistent-negative-bias effect

| Outcome | Safety off | Safety on | On-off effect | 95% paired bootstrap CI | Raw exact p | Holm p | Pair direction |
|---|---:|---:|---:|---:|---:|---:|---|
| Desired-replica MAE | 0.5861 | 0.0667 | -0.5194 (-88.6%) | [-0.5194, -0.5194] | 0.0625 | 0.125 | 5 negative |
| Deficient replica-seconds | 211 | 7 | -204 (-96.7%) | [-204, -204] | 0.0625 | 0.375 | 5 negative |
| Request P99 | 48.72 ms | 33.03 ms | -15.69 ms (-32.2%) | [-19.44, -11.94] | 0.0625 | 0.375 | 5 negative |
| Composite-SLO duration | 26.4 s | 17.2 s | -9.2 s (-34.8%) | [-18.8, 3.0] | 0.1875 | 0.375 | 4 negative, 1 positive |
| Oracle-relative excess replica-seconds | 0 | 17 | +17 | [17, 17] | 0.0625 | 0.125 | 5 positive |

Step 16 controller-cost accounting found 221 additional requested replica-seconds per run (1,105 total) and no additional net action transitions. This differs from the +17 oracle-relative excess metric: the first compares total safety-on versus safety-off requested occupancy, while the second compares requested replicas with the oracle. They answer different cost questions and must not be substituted.

Safety reduced aggregate Step 16 harm from 132 to 86 seconds (46 avoided; 34.8%), but one repetition increased from 13 to 26 harm seconds. All harm in these runs arose from the one-second completion-ratio component rather than P99 or failure-rate violation seconds.

## Missed-peak effect

| Outcome | Safety off | Safety on | On-off effect | 95% paired bootstrap CI | Raw exact p | Holm p | Pair direction |
|---|---:|---:|---:|---:|---:|---:|---|
| Desired-replica MAE | 1.0 | 0.2 | -0.8 (-80%) | [-0.8, -0.8] | 0.0625 | 0.125 | 5 negative |
| Deficient replica-seconds | 180 | 21 | -159 (-88.3%) | [-159, -159] | 0.0625 | 0.375 | 5 negative |
| Request P99 | 5197.66 ms | 2697.31 ms | -2500.35 ms (-48.1%) | [-3175.03, -1825.67] | 0.0625 | 0.375 | 5 negative |
| Composite-SLO duration | 60 s | 15 s | -45 s (-75%) | [-47.405, -42.2] | 0.0625 | 0.375 | 5 negative |
| Oracle-relative excess replica-seconds | 0 | 15 | +15 | [15, 15] | 0.0625 | 0.125 | 5 positive |

Step 16 controller-cost accounting found 174 additional requested replica-seconds and 2 additional scaling actions per run (870 replica-seconds and 10 actions total). Again, this is a safety-on minus safety-off occupancy premium, whereas +15 is oracle-relative excess.

## Intervention and readiness evidence

- Every safety-on run generated exactly one intervention and one clean release.
- First intervention sequence was 61 in every run.
- Maximum request was four replicas.
- Missed-peak readiness delays ranged from 1 to 6 s (mean 3.4 s).
- Persistent-bias readiness delay was 1 s in every run.
- Missed peaks retained 10-15 post-intervention harm seconds per run.

The logs support the mechanism: safety cannot protect the pre-detection window, and requested replicas cannot protect traffic until they become Ready. These delays explain residual harm without requiring a speculative mechanism.

## Safety-by-error interaction

The identified interaction is `(safety on-off)_missed - (safety on-off)_persistent-negative-bias` over five matched blocks.

- P99 benefit was 2484.66 ms larger for missed peaks, CI [-3155.83, -1813.49], exact p = 0.0625, Holm p = 0.1875.
- SLO reduction was 35.8 s larger for missed peaks, CI [-49.4, -26.8], exact p = 0.0625, Holm p = 0.1875.
- The deficient-replica reduction differed by +45 replica-seconds under the frozen interaction orientation; percentage protection was 88.3% for missed peaks and 96.7% for persistent bias. Absolute interaction signs must be interpreted alongside different off baselines.
- Missed peaks added 2 fewer oracle-relative excess replica-seconds than persistent bias.

Safety had a much larger latency/SLO benefit for missed peaks because the predictive controller supplied no event protection. For persistent bias, predictive control was already partially responsive and baseline P99 was low, leaving less latency harm to avoid while the safety floor remained active longer.

## Robustness

### SLO and capacity accounting

Offline analysis showed safety benefit for missed peaks under all six SLO definitions and all three capacity factors. Persistent-bias capacity benefit disappeared under the optimistic +10% capacity accounting because three replicas were treated as sufficient for 60 RPS.

### Trigger persistence

Step 19 prospectively compared 1 s versus 3 s persistence for missed peaks using controller v1.1.2 (5 matched pairs). Increasing persistence to 3 s:

- added 2.8 SLO seconds, CI [1.2, 4.2];
- added 61 Ready-deficit RPS-s, CI [43, 82];
- added 1269.66 ms P99, CI [703.38, 1872.82];
- saved 5.8 deployment replica-seconds, CI [-6.0, -5.4].

Thus faster detection improves protection at a small resource premium; the qualitative trade-off persists, but its magnitude is threshold-dependent.

## Combined Step 16 operational accounting

Across all ten safety pairs:

- harm fell from 432 to 161 seconds;
- avoided harm = 271 seconds (62.7% aggregate reduction);
- additional requested replica-seconds = 1,975;
- additional scaling actions = 10;
- mean readiness delay = 2.2 s.

This combined total is descriptive across two different errors and workloads; it is not a single pooled causal effect for a broader population.

## Statistical interpretation

With five pairs, the smallest possible two-sided exact p is 0.0625. None of the safety effects can cross p<0.05 under this design, and Holm-adjusted p-values are larger. The evidence is best described as large, consistently directed practical protection for deficiency and P99, with limited exact-test resolution. Persistent-bias SLO duration is additionally heterogeneous and its interval includes zero.

## Negative and constraining findings

1. Safety did not eliminate harm in either tested error.
2. One persistent-bias repetition had greater SLO harm with safety on.
3. Persistent-bias SLO uncertainty included zero.
4. Safety always added capacity under the analyzed cost metrics.
5. Missed peaks added command transitions; persistent bias changed occupancy/timing without adding net transitions.
6. A slower trigger saved a small amount of capacity but caused greater residual harm.
7. Only two underprediction structures were directly tested; false peaks, early/late timing, duration, placement, and shape received no direct safety ablation.
8. The experimental dispatched-demand signal may not be available with identical latency in production telemetry.

## Answer to the secondary RQ

The fixed reactive safety mechanism changed underprediction errors by raising a replica floor after observed overload, thereby converting much of decision deficiency and SLO harm into additional requested capacity. It was most effective for missed peaks, reducing deficient replica-seconds by 88.3%, request P99 by 48.1%, and SLO duration by 75%, while adding capacity and two action transitions per run. For persistent negative bias, it reduced deficiency by 96.7% and P99 by 32.2%, but SLO reduction was smaller and heterogeneous, and the capacity floor remained active longer. Detection persistence and Pod readiness caused residual harm; a faster trigger improved protection at a modest additional replica-second cost. These conclusions are causal for the two replayed errors under the fixed rule, not for forecast errors generally.

## Prohibited overclaims

- Do not say safety makes forecast quality unimportant.
- Do not say safety eliminates underprediction harm.
- Do not describe five-pair effects as conventionally significant at p<0.05.
- Do not combine total requested replica premium with oracle-relative excess without naming the denominator.
- Do not generalize the safety effect to error types that were not directly replayed.
- Do not generalize the dispatch-signal timing or capacity lookup to production systems without validation.
