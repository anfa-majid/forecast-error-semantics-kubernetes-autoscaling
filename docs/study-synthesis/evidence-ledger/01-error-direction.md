# Evidence Ledger 01 - Forecast-Error Direction

## Controlled contrast

- Contrast: persistent positive bias minus persistent negative bias.
- Workload: `sustained-peak-v1`.
- Inferential unit: matched run repetition.
- Sample: 8 matched pairs (16 Step 15 runs).
- Forecast control: MAE = 5 RPS, RMSE = 5 RPS, and transition MAE = 5 RPS for both conditions in every repetition.
- Estimand: B minus A, where A is persistent negative bias and B is persistent positive bias.

## Evidence

| Outcome | Negative bias (A) | Positive bias (B) | Paired effect B-A | 95% paired bootstrap CI | Raw exact p | Holm p | Pair direction |
|---|---:|---:|---:|---:|---:|---:|---|
| Desired-replica MAE | 0.5861 | 0 | -0.5861 (-100%) | [-0.5861, -0.5861] | 0.0078125 | 0.0546875 | 8 negative |
| Deficient replica-seconds | 211 | 0 | -211 (-100%) | [-211, -211] | 0.0078125 | 0.1640625 | 8 negative |
| Request P99 latency | 48.59 ms | 35.73 ms | -12.86 ms (-26.46%) | [-14.75, -10.79] | 0.0078125 | 0.1640625 | 8 negative |
| Composite-SLO duration | 24.875 s | 16.625 s | -8.25 s (-33.17%) | [-13.625, -3.5] | 0.03125 | 0.34375 | 6 negative, 2 ties |
| Excess replica-seconds | 0 | 0 | 0 | [0, 0] | 1 | 1 | 8 ties |

## Causal interpretation

Because the two forecasts have exactly equal MAE, RMSE, and transition MAE and were replayed as a controlled matched mutation, the direction change caused different controller decisions within this experimental system. At the sustained 60 RPS peak, the baseline capacity lookup treats three Ready replicas as 55 RPS and four as 65 RPS. The -5 RPS forecast lands at 55 RPS and therefore supports a three-replica decision, whereas the +5 RPS forecast lands at 65 RPS and supports four replicas. The negative error is harmful because it falls on the lower side of a discrete replica boundary.

## Safety evidence

For the persistent-negative-bias condition, safety on versus off (5 matched pairs) changed:

- deficient replica-seconds: 211 to 7, a reduction of 204 (-96.7%);
- request P99: reduction of 15.69 ms (-32.2%), 95% CI [-19.44, -11.94];
- mean SLO duration: reduction of 9.2 s, 95% CI [-18.8, 3.0];
- excess replica-seconds: increase of 17.

All five pairs agreed on deficient-capacity reduction, P99 reduction, and added excess capacity. With five pairs, the minimum possible two-sided exact p-value is 0.0625; the result is a large, consistent practical effect with limited test resolution, not a conventional p<0.05 finding.

## Robustness qualification

Offline Ready-capacity accounting at 90%, 100%, and 110% of the empirical lookup gave positive-minus-negative deficit effects of -1620, -900, and 0 RPS-seconds, respectively. Thus the controller-decision difference under the frozen policy is real, but the claim that it necessarily creates measured Ready-capacity deficit depends on the capacity calibration. At +10%, three replicas are credited with 60.5 RPS and are treated as sufficient for the 60 RPS peak.

## Negative finding

Positive bias did not create excess replica-seconds under the oracle-relative cost definition: both conditions recorded zero. The positive forecast requested the same four replicas as the oracle, so it was not overprovisioned relative to the reference policy. The study must not claim that every positive bias produces resource waste.

## Defensible claim

Under the tested sustained-peak workload and baseline capacity policy, changing only the direction of a persistent 5 RPS error changed the discrete replica decision and converted equal aggregate forecast error into different operational harm. Persistent underprediction caused decision error, deficiency, higher P99, and longer composite-SLO violation; equal overprediction did not impose oracle-relative excess capacity in this pair. The measured Ready-deficit component is capacity-calibration dependent.

## Prohibited overclaims

- Do not claim that positive bias always wastes replicas.
- Do not claim that negative bias always produces Ready-capacity deficit under every valid capacity model.
- Do not describe Holm-adjusted results as statistically significant at 0.05.
- Do not generalize beyond the tested controller, capacity boundary, sustained workload, and four-replica system.
