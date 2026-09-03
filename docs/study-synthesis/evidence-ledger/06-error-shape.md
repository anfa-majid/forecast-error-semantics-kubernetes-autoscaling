# Evidence Ledger 06 - Forecast Shape (Sharpened versus Smoothed)

## Controlled contrast

- Contrast: smoothed minus sharpened forecast shape.
- Workload: `periodic-triangle-v1`.
- Inferential unit: matched run repetition.
- Sample: 8 matched pairs (16 Step 15 runs).
- Accuracy controls were effectively exact: MAE = 0.29956 RPS, RMSE = 0.72668 RPS, and transition MAE = 0.33866 RPS for both conditions.
- Estimand: B minus A, where A is sharpened and B is smoothed.

## Evidence

| Outcome | Sharpened (A) | Smoothed (B) | Paired effect B-A | 95% paired bootstrap CI | Raw exact p | Holm p | Pair direction |
|---|---:|---:|---:|---:|---:|---:|---|
| Desired-replica MAE | 0 | 0 | 0 | [0, 0] | 1 | 1 | 8 ties |
| Deficient replica-seconds | 0 | 0 | 0 | [0, 0] | 1 | 1 | 8 ties |
| Excess replica-seconds | 0 | 0 | 0 | [0, 0] | 1 | 1 | 8 ties |
| Request P99 latency | 30.85 ms | 30.43 ms | -0.42 ms | [-2.05, 0.81] | 0.7578125 | 1 | 2 positive, 6 negative |
| Composite-SLO duration | 104.0 s | 104.5 s | +0.5 s | [-2.5, 3.75] | 0.8515625 | 1 | 4 positive, 4 negative |

## Causal interpretation

The shape mutation did not move the forecast across any replica-decision boundary under the tested periodic workload and controller policy. Consequently, sharpened and smoothed forecasts generated the same desired-replica trajectory as the oracle and the same capacity outcomes. Once controller actions are identical, small run-to-run P99 and SLO differences are attributable to experimental variability rather than the controlled shape mutation.

This is not evidence that forecast shape can never matter. It shows that shape differences below the controller's decision-resolution boundary can be operationally equivalent.

## SLO robustness

Across 200, 300, and 500 ms thresholds:

- composite smoothed-minus-sharpened differences were only +0.625, +0.5, and +0.5 s;
- pair directions were split 4 positive and 4 negative;
- leave-one-pair-out means crossed direction;
- latency-only SLO duration was zero for both conditions at 300 and 500 ms;
- at 200 ms, only one smoothed run contributed one latency-only violation second.

The negative result is robust to the tested SLO definitions.

## Safety evidence

No safety on/off ablation was run for the shape pair. Because the forecasts produced no deficient replica-seconds, there is no observed overload harm for safety to correct. It remains incorrect to report a safety treatment effect without a direct ablation.

## Metric interpretation

This pair is a case where conventional metrics did not mislead operationally: MAE, RMSE, and transition MAE were tied, and controller/action outcomes were also tied. The metrics did not identify the visual shape difference, but that distinction was irrelevant to this controller because it did not cross a decision threshold.

The defensible conclusion is not that MAE/RMSE predicted latency precisely. Rather, they correctly failed to rank two forecasts whose controlled shape difference produced no reproducible decision or operational difference.

## Negative and constraining findings

1. Shape alone did not alter replica decisions.
2. There was no deficiency or excess-capacity difference.
3. P99 difference was less than 1 ms and its interval crossed zero.
4. Composite-SLO difference was 0.5 s with exactly split pair directions.
5. No comparison approached statistical reliability.
6. All three forecast-error metrics were equal and the operational outcomes were effectively equal.

## Defensible claim

For the tested periodic-triangle workload, sharpened and smoothed forecasts with equal MAE, RMSE, and transition MAE produced identical replica decisions and capacity outcomes, with no reproducible latency or SLO difference. The shape mutation remained within the same replica-decision regions. This negative result bounds the study's contribution: forecast structure matters operationally when it changes threshold crossings, event lead time, or readiness, not merely because two traces have visibly different shapes.

## Prohibited overclaims

- Do not claim forecast shape never matters.
- Do not claim MAE/RMSE predict request latency from this pair.
- Do not interpret sub-millisecond P99 variation as a treatment effect.
- Do not infer a safety effect without a direct ablation.
