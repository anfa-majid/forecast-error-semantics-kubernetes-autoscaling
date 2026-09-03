# Step 18 Statistical Analysis Protocol

## Analysis population

The analysis uses all 142 accepted runs in the frozen Step 17 run-level table. The confirmatory mutation analysis uses the 112 Step 15 primary runs: seven accuracy-matched A/B contrasts with eight matched repetitions per side. The safety analysis uses ten Step 16 runs paired by condition and repetition to the corresponding ten Step 15 runs.

The run is the inferential unit. Seconds and repeated events within a run are not treated as independent replicates.

## Confirmatory estimands

For every contrast, the estimand is the paired difference `B - A`, except safety, which is `on - off`. Positive values therefore mean a larger outcome under B or safety-on. Contrast labels retain this direction explicitly.

Primary mutation contrasts are:

1. positive minus negative persistent bias;
2. shortened minus extended peak;
3. missed minus false peak;
4. transition-period minus stable-period error;
5. smoothed minus sharpened shape;
6. late minus early periodic event;
7. late minus early narrow spike.

Safety contrasts are estimated separately for persistent negative bias and missed peak.

## Outcomes and multiplicity families

- Forecast: MAE, RMSE, transition MAE.
- Decision: desired-replica MAE.
- Operational harm: deficient replica-seconds, request P99, SLO-violation seconds.
- Resource cost: excess replica-seconds.

Raw two-sided p-values are computed for every confirmatory contrast. Holm adjustment is applied across all tests within each domain and analysis family (primary mutations or safety). No outcome or finding is removed because it is negative or non-significant.

## Statistical methods

- Descriptives: n, individual run values, mean, standard deviation, median, Q1, Q3, and IQR.
- Difference uncertainty: deterministic paired nonparametric bootstrap percentile interval with 20,000 resamples, seed 1802026.
- Primary test: exact two-sided paired randomization/sign-flip test on the mean paired difference. With eight pairs there are 256 assignments; with five pairs there are 32.
- Effect sizes: absolute mean and median paired difference, percent change relative to the A/off mean when defined, paired standardized mean difference `dz`, and matched-pairs rank-biserial correlation.
- Sensitivity: leave-one-pair-out ranges for the mean difference and exact p-value; Wilcoxon-style signed-rank permutation p-value is supplementary.

Zero differences are retained. Undefined percentage effects and standardized effects are represented as missing with a reason rather than forced to zero.

## Interaction analysis

Only two interaction contrasts are identified by the realized design:

- `(late - early)_narrow-spike - (late - early)_periodic`, using matched repetition blocks;
- `(safety on - off)_missed-peak - (safety on - off)_persistent-negative-bias`, using matched repetition blocks.

These are difference-in-differences with exact sign-flip inference over block-level interaction differences and paired bootstrap intervals. A global error × workload × safety mixed-effects model is not identified because most errors occur in one workload and safety is available for only two errors.

The requested transient-versus-persistent comparison is not a randomized pair in the realized matrix. Any such comparison would conflate error form, workload, and forecast magnitude, so it is documented as non-estimable rather than presented as causal evidence.

## Ranking analysis

Rankings use condition-level medians from the 14 primary Step 15 conditions. Larger values mean worse outcomes/cost. Agreement is summarized using Spearman correlation, Kendall tau-b, top-one agreement, and pairwise ordering disagreement. Ranking analysis is supplementary and is not interpreted causally.

## Missingness and exclusions

No accepted run is excluded. Metrics unavailable by construction remain missing. Pairwise analyses require both members of the matched pair; any incomplete pair would be listed and excluded only for that outcome. The processor records pair counts for every test.

