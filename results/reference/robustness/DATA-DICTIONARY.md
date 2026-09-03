# Step 19 Final Output Data Dictionary

## Files

- `robustness-run-level.csv`: one row per retained prospective run (40 rows).
- `robustness-comparisons.csv`: one row per paired contrast and outcome (44 rows).
- `configuration-descriptives.csv`: count, mean, median, SD, Q1, and Q3 by prospective cell.
- `attempt-audit.csv`: all discovered campaign attempts and their disposition.
- `analysis-validation.json`: deterministic completion checks.
- `checksums.sha256`: SHA-256 hashes for generated datasets and figures.

## Core run-level fields and formulas

- `mae_rps`: mean absolute value of `forecast_rps − target_rps` over aligned seconds.
- `rmse_rps`: square root of the mean squared forecast error.
- `bias_rps`: mean signed forecast error.
- `controller_desired_replica_mae`: mean absolute difference between the main controller command and oracle replicas.
- `desired_replica_mae`: mean absolute difference between observed deployment desired replicas and oracle replicas; includes safety interventions.
- `deficient_replica_seconds`: sum of `max(oracle_replicas − deployment_desired_replicas, 0)` over one-second bins.
- `excess_replica_seconds`: sum of `max(deployment_desired_replicas − oracle_replicas, 0)`.
- `ready_deficient_replica_seconds`: sum of `max(required_replicas(target_rps) − deployment_ready_replicas, 0)`.
- `ready_capacity_deficit_rps_seconds`: sum of `max(target_rps − capacity(deployment_ready_replicas), 0)`.
- `replica_seconds`: sum of deployment desired replicas over one-second bins.
- `scale_action_count`: number of non-zero second-to-second changes in deployment desired replicas.
- `churn_magnitude_replicas`: sum of absolute second-to-second deployment desired-replica changes.
- `slo_violation_seconds`: count of aligned seconds in which P99 >300 ms, failure rate ≥1%, or completion ratio <99%.
- `slo_violation_rate`: SLO-violation seconds divided by analyzed seconds.
- `slo_episode_count`: number of false-to-true transitions in the composite-SLO indicator.
- `request_p99_latency_ms`: empirical 99th percentile of request-level latency.
- `request_failure_rate`: failed request records divided by all request records.
- `kubernetes_coverage` / `prometheus_coverage`: fraction of aligned seconds marked present for the source.

Capacity lookup: 0→0, 1→30, 2→40, 3→55, 4→65 RPS. Required replicas are the smallest lookup entry meeting target demand, capped at four.

## Comparison fields

- `configuration_a`, `configuration_b`: frozen contrast orientation.
- `mean_difference_b_minus_a`: mean of matched repetition differences.
- `percent_difference_vs_a`: paired mean difference divided by configuration-A mean.
- `bootstrap_ci_low/high`: deterministic 10,000-resample paired percentile interval.
- `exact_paired_permutation_p`: two-sided exact sign-permutation p-value.
- `all_pair_differences_same_direction`: whether all five differences are nonnegative or all nonpositive; zero counts as compatible with either direction.
- `pair_differences`: semicolon-separated differences in repetition order for transparent checking.

## Missing data

Numeric parsing failures become missing values. Aggregations ignore missing numeric observations, while source coverage remains explicitly reported. A retained run must have 180 aligned rows and pass the campaign's frozen validation. No imputation is used for request latency or source coverage.

