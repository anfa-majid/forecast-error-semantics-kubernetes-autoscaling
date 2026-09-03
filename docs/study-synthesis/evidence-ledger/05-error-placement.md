# Evidence Ledger 05 - Stable versus Transition-Period Error Placement

## Controlled contrast

- Contrast: transition-period error minus stable-period error.
- Workload: `gradual-ramp-v1`.
- Inferential unit: matched run repetition.
- Sample: 8 matched pairs (16 Step 15 runs).
- Aggregate-accuracy control: MAE = 1.0127 RPS and RMSE = 2.8463 RPS for both conditions in every repetition.
- Estimand: B minus A, where A is stable-period error and B is transition-period error.
- Transition MAE intentionally differs: 0 RPS for stable placement and 1.6 RPS for transition placement.

## Evidence

| Outcome | Stable (A) | Transition (B) | Paired effect B-A | 95% paired bootstrap CI | Raw exact p | Holm p | Pair direction |
|---|---:|---:|---:|---:|---:|---:|---|
| Transition MAE | 0 | 1.6 RPS | +1.6 | [1.6, 1.6] | 0.0078125 | 0.1640625 | 8 positive |
| Desired-replica MAE | 0.1146 | 0.1375 | +0.0229 (+20%) | [0.0229, 0.0229] | 0.0078125 | 0.0546875 | 8 positive |
| Deficient replica-seconds | 0 | 0 | 0 | [0, 0] | 1 | 1 | 8 ties |
| Excess replica-seconds | 55 | 66 | +11 (+20%) | [11, 11] | 0.0078125 | 0.0546875 | 8 positive |
| Request P99 latency | 32.98 ms | 31.81 ms | -1.17 ms | [-2.98, 0.26] | 0.25 | 1 | 4 negative, 4 positive |
| Composite-SLO duration | 64.75 s | 63.125 s | -1.625 s | [-5.75, 2.0] | 0.4921875 | 1 | 4 negative, 4 positive |

## Causal interpretation

With aggregate MAE and RMSE held equal, moving the error into the gradual workload transition caused a deterministic increase in transition MAE, a small increase in absolute replica-decision error, and 11 additional excess replica-seconds. It did not create deficient capacity. Under the tested mutation and controller thresholds, the affected transition decisions remained on the overprovisioning side of the oracle rather than delaying capacity needed by demand.

The operational effect was therefore additional resource cost, not reliability harm. P99 and SLO differences were small, crossed zero, and split evenly in direction across repetitions.

## SLO robustness

At 200, 300, and 500 ms:

- the composite transition-minus-stable difference was -1.625 s;
- pair directions were evenly split (4 negative, 4 positive);
- raw exact p = 0.4921875;
- latency-only SLO duration was zero for both conditions in every run.

The leave-one-pair-out composite mean remained slightly negative, but this does not overcome the pair heterogeneity, zero latency-only violations, or interval spanning zero. It is not evidence that transition placement improves reliability.

## Safety evidence

No safety on/off experiment was run for this pair. The absence of deficiency suggests the overload-trigger safety rule may have had little opportunity to act, but that is a mechanism-based expectation, not an observed safety result.

## Negative and constraining findings

1. Transition placement did not cause deficient replica capacity.
2. It did not reproduce a meaningful P99 or SLO penalty.
3. P99 and composite-SLO pair directions were exactly split.
4. Latency-only SLO duration was zero for both conditions at all tested thresholds.
5. Transition MAE correctly identified transition placement and aligned with a small decision/cost change, making it useful here where aggregate MAE/RMSE were tied.
6. No outcome crossed the prespecified Holm-adjusted 0.05 threshold; decision and cost outcomes reached 0.0546875.

## Defensible claim

For the tested gradual-ramp workload, placing an equal-MAE/RMSE error at the transition rather than a stable period caused a small, deterministic increase in replica-decision error and 11 excess replica-seconds, but no deficient capacity and no reproducible latency or SLO harm. Transition MAE distinguished the placement difference. This result constrains the broader hypothesis: transition-localized error is not inherently harmful; its consequence depends on error direction, threshold crossing, and whether the affected decision creates under- or overprovisioning.

## Prohibited overclaims

- Do not claim transition placement generally worsens SLO reliability.
- Do not interpret the small negative mean P99/SLO differences as a protective effect.
- Do not infer safety behavior; it was not tested.
- Do not generalize from one gradual-ramp mutation to all transition errors.
