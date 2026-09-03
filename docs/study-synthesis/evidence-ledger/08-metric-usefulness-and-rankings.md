# Evidence Ledger 08 - Metric Usefulness and Ranking Agreement

## Purpose and evidence status

This section answers when aggregate forecast metrics are informative, when they fail, and whether forecast, decision, and operational rankings are interchangeable.

Two evidence types must remain separate:

1. Controlled accuracy-matched pairs establish causal differences that MAE/RMSE cannot distinguish within those pairs.
2. Correlations across 14 condition medians are supplementary associations; they do not establish that one metric causes or predicts another outside this dataset.

## Controlled evidence: where aggregate metrics fail

MAE and RMSE were equal by design within all seven primary contrasts, yet large operational differences occurred in several:

- positive versus negative bias: 211 deficient replica-seconds and 12.86 ms P99 difference;
- shortened versus extended: 90 deficient versus 90 excess replica-seconds and 1543.79 ms P99 difference;
- missed versus false peak: 180 deficient versus 120 excess replica-seconds and 4805.43 ms P99 difference;
- late versus early narrow spike: identical replica-error summaries but 2565.51 ms P99 and 8.625 s SLO differences.

These controlled comparisons establish that equal MAE/RMSE is insufficient to infer equal operational consequence when error direction, event presence, duration, or lead time differs.

## Controlled evidence: where tied metrics were appropriate

### Shape pair

Sharpened and smoothed forecasts had equal MAE, RMSE, and transition MAE and produced identical controller decisions, deficiency, and excess capacity. Their P99 and SLO differences were negligible and uncertain. Here, tied conventional metrics appropriately corresponded to operational equivalence under the controller.

### Periodic timing pair

Equal early/late MAE and RMSE corresponded to identical desired-replica MAE, deficiency, and excess capacity. P99 differed by only 3.40 ms and composite-SLO uncertainty included zero. Conventional metrics were not sufficient to explain every millisecond, but their tie did not conceal a material controller/capacity difference in this workload.

Thus MAE/RMSE do not always fail; they fail when the omitted structure changes a decision boundary or readiness timing.

## Transition MAE usefulness and limitations

Transition MAE identified several structures hidden by aggregate MAE/RMSE:

- extended versus shortened peak: 17.5 versus 0 RPS;
- missed versus false peak: 17.5 versus 0 RPS;
- transition versus stable placement: 1.6 versus 0 RPS;
- late versus early narrow spike: 35 versus 0 RPS.

It correctly flagged transition/event-placement differences that were operationally meaningful in the duration, missed-peak, and late-spike comparisons. It also flagged transition placement when the result was only 11 excess replica-seconds and no SLO harm. Therefore transition MAE is more structurally sensitive, but a high value is not itself proof of harm.

For periodic early/late timing, transition MAE differed by only 0.0146 RPS and operational differences were small. For sharpened/smoothed shape, it tied and outcomes tied.

## Ranking agreement across 14 condition medians

Selected associations:

| Metric pair | Spearman rho | Kendall tau-b | Top-one agreement | Pairwise disagreement |
|---|---:|---:|---|---:|
| MAE - desired-replica MAE | 0.786 | 0.686 | No | 14.6% |
| RMSE - desired-replica MAE | 0.749 | 0.588 | No | 19.5% |
| Desired-replica MAE - deficient replica-seconds | 0.718 | 0.645 | No | 13.4% |
| MAE - deficient replica-seconds | 0.635 | 0.490 | No | 21.5% |
| RMSE - request P99 | 0.427 | 0.375 | No | 30.6% |
| MAE - request P99 | 0.257 | 0.229 | No | 38.1% |
| RMSE - SLO duration | -0.573 | -0.443 | No | 72.9% |
| MAE - SLO duration | -0.097 | -0.183 | Yes | 59.5% |
| Request P99 - SLO duration | -0.319 | -0.231 | No | 61.5% |
| Deficient - excess replica-seconds | -0.049 | -0.056 | No | 53.6% |

## Interpretation of useful associations

- MAE and RMSE were reasonably aligned with average desired-replica error across conditions.
- Desired-replica MAE was strongly aligned with deficient replica-seconds.
- MAE showed moderate alignment with deficiency.
- RMSE showed moderate, not strong, alignment with request P99.

These results show that conventional accuracy can be useful for coarse condition-level screening, particularly for controller-decision error. It should not be discarded.

## Interpretation of disagreement

- Forecast rankings did not reproduce tail-latency, SLO-duration, or excess-capacity rankings reliably.
- RMSE and composite-SLO duration were negatively associated in this condition set, demonstrating that larger squared forecast error did not imply greater measured composite harm.
- P99 and SLO duration also disagreed because P99 measures tail magnitude while SLO duration counts violating seconds and includes failure/completion components.
- Deficiency and excess capacity describe opposite cost/harm directions and were essentially uncorrelated.

Top-one agreement alone is insufficient. MAE and SLO duration shared a top-ranked condition through ties while disagreeing on 59.5% of comparable pair orderings and having near-zero/negative rank correlation.

## SLO-ranking robustness

Changing the numerical latency threshold within the composite SLO preserved rankings:

- 200 ms: Spearman 1.0, Kendall 1.0, top-one agreement yes, 0 pairwise disagreement;
- 500 ms: Spearman 0.9989, Kendall 0.9945, top-one agreement yes, 0 pairwise disagreement among comparable pairs.

Changing the construct to latency-only did not preserve rankings:

- Spearman versus baseline composite = -0.1254;
- Kendall = -0.0699;
- top-one agreement absent;
- 55.6% pairwise disagreement.

Thus conclusions about SLO rankings are robust to the threshold within the composite construct but not to replacing the construct itself.

## Negative and constraining findings

1. Aggregate metrics performed appropriately for the shape pair and approximately for periodic timing.
2. Transition MAE was informative but did not map monotonically to harm.
3. MAE/RMSE had useful associations with decision error; they are incomplete, not useless.
4. Top-one agreement can coexist with broad ranking disagreement.
5. Condition-level analysis contains only 14 units and many ties.
6. Ranking correlations are not causal evidence and should not be used to explain the controlled mechanisms.
7. The negative RMSE-SLO association is dataset-specific and not evidence that improving RMSE worsens reliability.

## Defensible metric claim

MAE and RMSE provide useful coarse information about forecast magnitude and are moderately to strongly associated with replica-decision error across the tested conditions, but they are insufficient for operational ranking when error direction, event presence, duration, or readiness timing differs. Transition MAE detects several important event-local structures, yet it also cannot determine whether a transition error becomes deficiency, excess cost, or no material harm. Operational evaluation therefore requires a metric set spanning forecast error, decision error, Ready-capacity deficiency, tail magnitude, SLO duration, and resource excess rather than a single universal score.

## Prohibited overclaims

- Do not say MAE and RMSE are useless.
- Do not interpret rank correlations as causal or predictive validation outside the 14 conditions.
- Do not say transition MAE is universally superior.
- Do not combine P99 magnitude and SLO duration as interchangeable reliability measures.
- Do not infer that higher RMSE improves SLO outcomes from the negative association.
