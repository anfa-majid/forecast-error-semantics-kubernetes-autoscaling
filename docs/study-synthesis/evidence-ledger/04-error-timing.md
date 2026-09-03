# Evidence Ledger 04 - Forecast-Error Timing and Workload Interaction

## Controlled contrasts

Two accuracy-matched early/late contrasts were analyzed separately:

1. periodic workload (`pair-06-timing_periodic`), 8 matched pairs;
2. narrow spike (`pair-07-timing_spike`), 8 matched pairs.

The estimand is late minus early. MAE and RMSE were exactly equal within each workload:

- periodic: MAE 6.5294 RPS; RMSE 7.3618 RPS;
- narrow spike: MAE 4.0230 RPS; RMSE 11.8661 RPS.

Transition MAE was almost equal for periodic traffic (7.6533 early versus 7.6679 late), but strongly distinguished the narrow spike (0 early versus 35 RPS late).

## Periodic-workload evidence

| Outcome | Early | Late | Late-early effect | 95% paired bootstrap CI | Raw exact p | Holm p |
|---|---:|---:|---:|---:|---:|---:|
| Desired-replica MAE | 0.4583 | 0.4583 | 0 | [0, 0] | 1 | 1 |
| Deficient replica-seconds | 165 | 165 | 0 | [0, 0] | 1 | 1 |
| Excess replica-seconds | 165 | 165 | 0 | [0, 0] | 1 | 1 |
| Request P99 latency | 30.68 ms | 34.08 ms | +3.40 ms | [1.95, 4.91] | 0.0078125 | 0.1640625 |
| Composite-SLO duration | 104.375 s | 107 s | +2.625 s | [-1.625, 6.75] | 0.3515625 | 1 |

Periodic early and late forecasts produced identical replica-error, deficiency, and excess-capacity summaries. The P99 effect was small in absolute terms, and the SLO effect was uncertain and directionally heterogeneous (5 positive, 3 negative).

## Narrow-spike evidence

| Outcome | Early | Late | Late-early effect | 95% paired bootstrap CI | Raw exact p | Holm p |
|---|---:|---:|---:|---:|---:|---:|
| Desired-replica MAE | 0.3333 | 0.3333 | 0 | [0, 0] | 1 | 1 |
| Deficient replica-seconds | 30 | 30 | 0 | [0, 0] | 1 | 1 |
| Excess replica-seconds | 30 | 30 | 0 | [0, 0] | 1 | 1 |
| Request P99 latency | 29.95 ms | 2595.46 ms | +2565.51 ms | [2233.30, 2954.57] | 0.0078125 | 0.1640625 |
| Composite-SLO duration | 11.25 s | 19.875 s | +8.625 s (+76.7%) | [4.5, 13.5] | 0.0078125 | 0.1640625 |

All eight narrow-spike pairs showed higher P99 and longer SLO duration for the late forecast, despite identical absolute desired-replica error and identical deficient/excess desired-replica seconds.

## Identified workload interaction

The prespecified difference-in-differences was `(late-early)_spike - (late-early)_periodic`.

- P99 interaction: +2562.12 ms, 95% CI [2226.89, 2953.05], raw p = 0.0078125, Holm-adjusted p = 0.0234375, all 8 blocks positive.
- SLO-duration interaction: +6.0 s, CI [-1.25, 13.125], raw p = 0.15625, Holm-adjusted p = 0.3125.
- Desired-replica MAE, deficient replica-seconds, and excess replica-seconds interactions were exactly zero.

The P99 interaction is the clearest multiplicity-adjusted inferential result in the study: the operational effect of lateness was substantially larger for a narrow spike than for periodic traffic.

## Causal mechanism

For the narrow spike, early forecasting places the scale-out request before the short demand event, allowing capacity to become Ready before or near onset. Late forecasting shifts the same broad error magnitude after onset; the remaining lead time is shorter than readiness delay, so requests encounter insufficient Ready capacity during the most consequential seconds. Absolute desired-replica error integrates the shifted trajectories and is identical, but does not encode whether capacity was Ready when the spike arrived.

Periodic traffic repeatedly revisits similar demand states and has broader/repeated transitions. Shifting the forecast early or late produced the same aggregate controller trajectory and allowed later cycles and existing replicas to dilute the timing consequence. This mechanism is supported within the tested workloads; it should not be generalized to every periodic process without further experiments.

## SLO robustness

For the narrow spike, late-minus-early SLO duration remained positive under all tested definitions:

- composite: +8.625 s at 200, 300, and 500 ms;
- latency-only: +8.75, +8.75, and +7.875 s at 200, 300, and 500 ms.

All eight pairs and every leave-one-pair-out estimate retained the direction.

For periodic traffic, latency-only differences were 0, -0.125, and 0 seconds across the thresholds, and composite differences were only +2.625 to +2.75 seconds with mixed pair directions. Therefore, a general claim that late forecasts are always worse is not supported.

## Forecast-horizon robustness

Step 19 prospectively compared 3 s and 9 s horizons for the narrow-spike pair (5 matched pairs per early/late side).

For late forecasts, increasing horizon from 3 to 9 s:

- reduced SLO duration by 16.2 s, CI [-21.8, -10.6];
- reduced request P99 by 1080.50 ms, CI [-1535.24, -544.70];
- reduced Ready-capacity deficit by 216 RPS-s, CI [-242, -179];
- reduced deficient replica-seconds by 17.4, CI [-18, -16.2].

All five pairs agreed; exact p = 0.0625 for these nonzero effects.

For early forecasts, 9 s versus 3 s reduced SLO duration by 7.8 s and P99 by 4.75 ms, while deficiency remained exactly zero. Horizon therefore moderated both sides but delivered a much larger capacity/readiness benefit for late forecasts.

## Safety evidence

No direct safety on/off ablation was performed for the early/late pair. Safety effects from missed peaks cannot be assigned to timing errors without data. The horizon experiment is the relevant prospective timing robustness check.

## Negative and constraining findings

1. Periodic early and late forecasts produced identical replica decisions and capacity summaries.
2. Narrow-spike early and late forecasts also had identical absolute desired-replica error and deficient/excess desired-replica seconds, even while latency differed by seconds.
3. Periodic SLO differences were small, mixed, and non-significant.
4. Transition MAE detected late narrow-spike placement but provided almost no separation for the periodic pair.
5. Direct safety correction of early/late timing was not tested.

## Defensible claim

Forecast timing had a workload-dependent causal effect. With matched MAE/RMSE, late versus early prediction produced little operational difference for the tested periodic workload but caused severe P99 and SLO harm for a narrow spike. The identified P99 interaction was +2562 ms and survived Holm correction. The mechanism was lead time relative to readiness: late spike forecasts requested capacity too close to or after demand onset, whereas early forecasts allowed capacity to become Ready. A longer horizon substantially reduced this harm. Aggregate desired-replica error did not capture the readiness-timing consequence.

## Prohibited overclaims

- Do not state that late forecasts are always worse across workloads.
- Do not claim early/late timing changed aggregate replica-error magnitude in these pairs.
- Do not infer a direct safety effect for timing; it was not tested.
- Do not interpret ranking or cross-workload associations as the causal evidence; the matched contrasts and interaction are the causal evidence.
