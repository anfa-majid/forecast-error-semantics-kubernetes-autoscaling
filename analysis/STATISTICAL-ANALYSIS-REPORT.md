# Step 18 — Statistical Analysis Report

## Executive conclusion

The controlled mutations show large, directionally consistent practical differences even when conventional significance thresholds are difficult to reach with eight pairs. Missed peaks, shortened peaks, late narrow spikes, and persistent underprediction produced the clearest operational harm. False or extended peaks primarily converted error into excess capacity. The reactive safety net substantially reduced harm for both tested underprediction errors, but added capacity, and five pairs are insufficient for a two-sided exact test to attain `p < 0.05` (minimum possible p is 0.0625).

After Holm correction within the prespecified domain families, no primary or safety comparison crossed 0.05. This is reported as a power/multiplicity limitation, not as evidence of no effect. Exact raw p-values, confidence intervals, effect sizes, all individual points, and negative findings are retained.

## Design and methods

The inferential unit is one matched run repetition. Seven Step 15 comparisons contain eight A/B pairs each. Step 16 contributes two safety on/off comparisons with five pairs each. Individual seconds and the five events within periodic runs were not promoted to independent replicates.

The primary test is an exact two-sided sign-flip test of the mean paired difference. Uncertainty is a 20,000-resample paired bootstrap percentile interval. Effects include the absolute and percentage mean difference, paired standardized effect (`dz`), and matched-pairs rank-biserial correlation. Holm adjustment is applied within forecast, decision, harm, and cost domains separately for primary and safety analyses. The complete frozen protocol is in `ANALYSIS-PROTOCOL.md`.

Because several engineered metrics are identical across repetitions, some confidence intervals collapse to a point and `dz` is undefined when the paired-difference standard deviation is zero. In those cases the absolute difference and rank-biserial effect remain interpretable.

## Main controlled comparisons

Differences below are B minus A. Confidence intervals are paired bootstrap 95% intervals; p-values are exact and unadjusted, with multiplicity conclusions stated separately.

### Missed versus false peak

Compared with a false peak, a missed peak added 180 deficient replica-seconds in every pair, increased request P99 by 4,805 ms (95% CI 4,101 to 5,503), and added 49.25 SLO-violation seconds (95% CI 43.38 to 55.25). It reduced excess capacity by 120 replica-seconds. Raw exact p was 0.0078125 for all four contrasts. Thus equal MAE and RMSE concealed a strong harm-versus-cost asymmetry.

### Shortened versus extended peak

A shortened forecast added 90 deficient replica-seconds and increased request P99 by 1,544 ms (95% CI 1,269 to 1,867), while removing 90 excess replica-seconds. SLO duration increased by 6 seconds, but its exact p was 0.1016 and the paired outcomes were less consistent. This is evidence that timing/duration direction changes the type of consequence even when aggregate accuracy is held equal.

### Persistent positive versus negative bias

Positive bias eliminated the 211 deficient replica-seconds observed under negative bias and lowered request P99 by 12.86 ms (95% CI 10.79 to 14.75 lower). Mean SLO duration was 8.25 seconds lower (95% CI 3.5 to 13.63 lower). The main controller recorded no excess replica-seconds for either member under this metric, so the anticipated overprovisioning premium was not captured as run-level excess desired capacity in this pair.

### Late versus early

For periodic traffic, late forecasts increased request P99 by only 3.40 ms (95% CI 1.95 to 4.91) and did not change deficient/excess replica-seconds; the 2.63-second SLO difference was uncertain. For a narrow spike, lateness increased request P99 by 2,566 ms (95% CI 2,233 to 2,955) and SLO duration by 8.63 seconds (95% CI 4.5 to 13.5). The workload interaction in P99 was 2,562 ms (exact p 0.0078125; Holm-adjusted within interaction harm outcomes 0.02344). Timing error is therefore strongly workload-shape dependent.

### Stable versus transition placement

Moving the error to the transition increased excess capacity by 11 replica-seconds but produced no deficient replica-seconds. P99 changed by -1.17 ms (95% CI -2.98 to 0.26), and SLO duration by -1.63 seconds (95% CI -5.75 to 2.0). These operational differences are small and uncertain despite a deterministic increase in transition MAE.

### Sharpened versus smoothed shape

The shape pair produced no differences in MAE, decision error, deficient capacity, or excess capacity. P99 differed by -0.42 ms (95% CI -2.05 to 0.81) and SLO duration by 0.5 seconds (95% CI -2.5 to 3.75). This is a retained negative result: under this controller and workload, the engineered shape distinction did not translate into a reproducible operational effect.

## Reactive safety ablation

For persistent negative bias, safety reduced deficient capacity from 211 to 7 replica-seconds (-96.7%), reduced P99 by 15.69 ms (-32.2%; 95% CI -19.44 to -11.94), and reduced mean SLO duration by 9.2 seconds, though its CI included zero (-18.8 to 3.0). It added 17 excess replica-seconds.

For missed peaks, safety reduced deficient capacity from 180 to 21 replica-seconds (-88.3%), reduced P99 by 2,500 ms (-48.1%; 95% CI -3,175 to -1,826), and reduced SLO duration from 60 to 15 seconds (-75%; 95% CI -47.41 to -42.2). It added 15 excess replica-seconds.

All five paired directions agreed for deficient capacity, P99, and added excess capacity. Nevertheless, a two-sided exact test with five pairs has minimum p 0.0625, so these comparisons cannot attain p < 0.05. The evidence supports a large, consistent practical benefit with limited inferential resolution, not a conventional significance claim.

The safety-by-error interaction indicates 35.8 seconds more SLO reduction for missed peaks than persistent bias and a 2,485 ms larger P99 reduction. Its exact p is also bounded at 0.0625.

## Multiplicity and power

No primary or safety effect retained `p < 0.05` after Holm adjustment over all tests in its domain family. Several raw exact p-values were 0.0078125—the smallest possible with eight pairs—but the forecast/harm domains contain multiple contrasts. Cost and decision effects reached adjusted 0.05469 for some primary comparisons, narrowly above 0.05.

This result should be interpreted alongside effect magnitude, direction consistency, and confidence intervals. The experiment was optimized for controlled paired contrasts but has low discrete-test resolution. A future confirmatory replication should prespecify one operational primary outcome per hypothesis or increase repetitions; the present analysis must not retroactively narrow families to manufacture significance.

## Ranking agreement

Forecast and operational rankings were not interchangeable. MAE correlated strongly with desired-replica MAE (Spearman 0.786; Kendall 0.686) and desired-replica MAE with deficient replica-seconds (Spearman 0.718; Kendall 0.645). In contrast, RMSE versus SLO duration was negatively associated (Spearman -0.573; Kendall -0.443), and request P99 versus SLO duration was also negative (Spearman -0.319).

Top-one agreement was generally absent, and many metric pairs disagreed on substantial fractions of comparable condition pairs. This directly supports using multiple outcome-specific rankings. These correlations are supplementary summaries of 14 condition medians and are not causal evidence.

## Non-estimable requested comparison

The realized matrix contains persistent bias conditions but no accuracy-matched, randomized transient-versus-persistent pair. Comparing a transient event error against persistent bias would also change workload and error magnitude. Therefore this requested contrast is not reported as causal. The distinction can be tested in a future factorial extension.

## Limitations

- Eight pairs provide coarse exact-test resolution; five safety pairs cannot yield a two-sided exact p below 0.05.
- Error type and workload are partly coupled, preventing the proposed global mixed-effects interaction model from being uniquely identified.
- Bootstrap intervals quantify sampling variability across observed matched runs but do not replace randomization inference.
- Condition-level ranking analysis has only 14 units and many ties.
- Step 16 Pod-event fields remain unavailable as documented in Step 17; the analyzed Ready and operational metrics remain available.
- Results apply to the tested controller, capacity model, workload shapes, forecast horizon, and Azure/K3s environment.

## Research conclusion

Aggregate forecast accuracy alone did not predict operational consequence. Controlled direction, duration, event presence, and timing mutations with equal MAE/RMSE frequently produced different harm-versus-cost outcomes. Missed peaks and late narrow spikes were especially harmful; false and extended peaks predominantly spent resources. The fixed reactive safety rule converted much of underprediction harm into a modest excess-capacity premium, with the clearest benefit for missed peaks. Negative results for shape and stable/transition placement are retained and constrain the generality of the conclusion.

## Figure guide

1. `figures/figure-01-primary-effect-forest.svg` shows all seven primary paired effects for all eight prespecified metrics with bootstrap intervals and raw exact p-values. It is the main quantitative overview.
2. `figures/figure-02-safety-paired-runs.svg` shows every safety off/on repetition for deficient capacity, P99, SLO duration, and excess capacity. The consistent harm reduction and resource premium are visible without relying on aggregate bars.
3. `figures/figure-03-ranking-spearman.svg` displays the Spearman agreement matrix across the eight condition-level rankings.
4. `figures/figure-04-ranking-disagreement.svg` displays pairwise ordering-disagreement rates, including ties only when both metrics yield a comparable ordering.
5. `figures/figure-05-harm-versus-cost.svg` places all 14 primary conditions on the SLO-harm versus excess-capacity plane; marker size represents P99.
6. `figures/figure-06-primary-slo-paired-runs.svg` shows every matched SLO-duration observation in the seven primary contrasts, retaining heterogeneous and negative results.

All figures are SVG vector graphics suitable for lossless scaling in the dissertation or paper. Figure values are generated directly from the sealed CSV outputs rather than transcribed manually.
