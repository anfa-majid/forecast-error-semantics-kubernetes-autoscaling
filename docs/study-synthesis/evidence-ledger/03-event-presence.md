# Evidence Ledger 03 - Event Presence (Missed versus False Peak)

## Controlled contrast

- Contrast: missed peak minus false peak.
- Workload: `narrow-spike-v1`.
- Inferential unit: matched run repetition.
- Sample: 8 matched pairs (16 Step 15 runs).
- Aggregate-accuracy control: MAE = 6.0345 RPS and RMSE = 14.5330 RPS for both forecasts in every repetition.
- Estimand: B minus A, where A is false peak and B is missed peak.
- Transition MAE was not matched: false peak = 0 and missed peak = 17.5 RPS under the frozen transition definition.

## Evidence

| Outcome | False peak (A) | Missed peak (B) | Paired effect B-A | 95% paired bootstrap CI | Raw exact p | Holm p | Pair direction |
|---|---:|---:|---:|---:|---:|---:|---|
| Desired-replica MAE | 0.6667 | 1.0 | +0.3333 (+50%) | [0.3333, 0.3333] | 0.0078125 | 0.0546875 | 8 positive |
| Deficient replica-seconds | 0 | 180 | +180 | [180, 180] | 0.0078125 | 0.1640625 | 8 positive |
| Request P99 latency | 31.50 ms | 4836.93 ms | +4805.43 ms | [4101.49, 5503.29] | 0.0078125 | 0.1640625 | 8 positive |
| Composite-SLO duration | 12.75 s | 62 s | +49.25 s (+386.3%) | [43.375, 55.25] | 0.0078125 | 0.1640625 | 8 positive |
| Excess replica-seconds | 120 | 0 | -120 (-100%) | [-120, -120] | 0.0078125 | 0.0546875 | 8 negative |

## Causal interpretation

The forecasts have identical aggregate MAE and RMSE, but place the same broad error budget on opposite event-presence mistakes. A missed peak withholds scale-out during real high demand, producing 180 deficient replica-seconds, multi-second request P99, and prolonged SLO harm. A false peak requests capacity for demand that never occurs, producing 120 excess replica-seconds without measured deficiency. Within this controlled pair, event presence causally determines whether aggregate error becomes reliability harm or resource cost.

## Robustness

### SLO definition

Missed-minus-false SLO duration remained positive in all six tested definitions:

- composite SLO: +49.25 s at 200 and 300 ms; +49.125 s at 500 ms;
- latency-only: +33.5 s at 200 and 300 ms; +32.75 s at 500 ms.

Every matched pair and every leave-one-pair-out estimate retained the same direction; raw exact p = 0.0078125 in every scenario.

### Capacity accounting

Missed-minus-false Ready-capacity deficit remained positive under all capacity factors:

- 90% lookup: +1200.75 RPS-s;
- baseline lookup: +1183.125 RPS-s;
- 110% lookup: +1120.5 RPS-s.

All eight pairs and every leave-one-pair-out estimate retained the direction. This asymmetry is not an artifact of the baseline Pod-capacity estimate.

## Safety evidence

For missed peaks, safety on versus off (5 matched pairs) changed:

- desired-replica MAE: 1.0 to 0.2 (-80%);
- deficient replica-seconds: 180 to 21 (-159; -88.3%);
- request P99: 5197.66 to 2697.31 ms (-2500.35 ms; -48.1%), 95% CI [-3175.03, -1825.67];
- composite-SLO duration: 60 to 15 s (-45 s; -75%), 95% CI [-47.405, -42.2];
- excess replica-seconds: 0 to 15 (+15).

All five pairs agreed on every listed harm reduction and on added excess capacity. Exact two-sided p = 0.0625, the minimum possible with five pairs; Holm-adjusted harm p = 0.375.

Safety reduced but did not eliminate harm: 21 deficient replica-seconds, approximately 2.7 s request P99, and 15 SLO seconds remained on average. Reactive intervention begins only after observed overload persists and new capacity still requires readiness time.

## Safety-threshold robustness

In the Step 19 replacement campaign, increasing overload persistence from 1 to 3 seconds for missed peaks:

- added 2.8 SLO seconds, 95% CI [1.2, 4.2];
- added 61 Ready-capacity-deficit RPS-s, CI [43, 82];
- added 1269.66 ms request P99, CI [703.38, 1872.82];
- used 5.8 fewer deployment replica-seconds, CI [-6.0, -5.4].

Thus faster intervention improves protection at a small capacity premium. Safety performance is conditional on the frozen trigger persistence and readiness delay.

## Negative and constraining findings

1. Safety did not prevent initial harm and did not restore the missed-peak run to false-peak behavior.
2. Safety added capacity cost; it converted rather than erased part of the consequence.
3. Transition MAE distinguished the pair, so aggregate MAE/RMSE are not the only available forecast diagnostics.
4. With five pairs, safety effects cannot meet conventional two-sided p<0.05.
5. False peaks are not harmless: their principal observed consequence was 120 excess replica-seconds, not SLO harm.

## Defensible claim

For the tested narrow-spike workload, equal-MAE/RMSE missed and false peaks caused a robust harm-versus-cost asymmetry. Missing a real event produced severe deficient capacity, tail latency, and SLO duration, whereas predicting a nonexistent event primarily produced excess replica cost. The fixed reactive safety rule corrected most but not all missed-peak harm and exchanged that protection for additional capacity. This direction survived all tested SLO definitions, capacity assumptions, and leave-one-pair-out checks.

## Prohibited overclaims

- Do not call false peaks operationally harmless; they incur resource cost.
- Do not say safety eliminated missed-peak harm.
- Do not claim safety was conventionally significant at p<0.05 with five pairs.
- Do not claim MAE/RMSE were the only metrics examined; transition MAE distinguished the pair.
- Do not generalize the exact effects beyond the tested spike, controller, four-replica bound, and cluster.
