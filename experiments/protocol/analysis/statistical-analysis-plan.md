# Statistical Analysis Plan

## Analysis population

The primary analysis includes all technically valid safety-disabled matched runs. The run is the unit of observation. A technical failure is not analyzed but remains in the audit ledger and is replaced only within the same preassigned matrix cell.

## Estimands

For each of seven forecast pairs, calculate B minus A within the same repetition block. The primary estimand is the median paired difference in deficient ready-replica-seconds. Positive values mean side B caused more capacity deficiency. Secondary estimands use the same direction for excess ready-replica-seconds, SLO-violation seconds, P99 latency, failure rate, completion ratio, and scale-up lateness.

## Inference

Use a two-sided exact sign-flip paired permutation test for the primary outcome when the data permit exact enumeration. Report the raw p-value and Holm-adjusted p-value across seven pair-specific primary tests. Report the paired median difference and a 95% percentile bootstrap confidence interval using seed 14002. Use the Wilcoxon signed-rank test as a sensitivity analysis; zero differences are handled with the Pratt convention.

Secondary outcomes are descriptive/exploratory: report paired median, interquartile range, mean, standard deviation, effect direction, and unadjusted 95% intervals. Do not recast secondary findings as confirmatory.

## Oracle and safety analyses

Oracle runs describe the achievable same-policy reference by workload and are not pooled into matched-error hypothesis tests. Safety-on runs are compared descriptively with their corresponding safety-off condition; because safety-on has five repetitions and safety-off has eight, use repetition blocks 1–5 for the prespecified paired safety contrast.

## Missing and outliers

No outcome imputation and no statistical outlier deletion are allowed. Technically valid extreme observations remain. Technical invalidity follows only the frozen protocol. Report the number of failed attempts, replacement attempts, and reasons by condition.
