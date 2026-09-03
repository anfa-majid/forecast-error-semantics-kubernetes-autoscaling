# Step 17 Analysis-Ready Dataset — Data Dictionary

## 1. Dataset population

The dataset contains only accepted attempts: 132 Step 15 safety-off runs and 10 Step 16 safety-on runs. The primary run key is `run_id`; the accepted attempt is retained in `attempt`. Raw attempt directories are read-only inputs and are never rewritten.

## 2. Alignment rules

- Common interval: half-open one-second bins `[t, t+1)` relative to workload T0.
- Workload: `target_rps` at `offset_ms / 1000`.
- Forecast: `predicted_rps` is joined to workload time using `target_offset_ms`, not `issued_offset_ms`. The first six workload seconds therefore have no target-aligned forecast and remain missing.
- Controller desired replicas: predictive `commanded_replicas` for Step 15; arbitrated `final_commanded_replicas` for Step 16.
- Oracle desired replicas: `commanded_replicas` from the frozen oracle-decision input.
- Ready replicas: normalized Kubernetes snapshots for Step 15; the safety controller's live Deployment Ready read for Step 16.
- Requests: dispatch belongs to `source_second`; raw request latency remains request-level for run/event P99.
- CPU and memory: one-second normalized Prometheus values.
- Pod events: unique Pod UID creation and Ready transition timestamps aligned to T0 for Step 15. Step 16 Pod events are unavailable because its remote Kubernetes collector could not invoke `kubectl`; they are missing, never zero-filled.

## 3. Missing-data rules

- CSV missing numeric values are empty; JSON equivalents are `null`.
- Missing values are not coerced to zero.
- Forecast metrics use only seconds with a target-aligned forecast (`forecast_aligned_seconds`).
- A missing predicted event onset is represented by an empty value plus `onset_missing_reason=forecast_does_not_cross_event_threshold`.
- Readiness delay is missing when no scale-up occurs or the requested count is not observed Ready before run end.
- Step 16 Pod-event counts are missing with `pod_event_source=unavailable_step16_remote_kubectl`.
- `normalized_kubernetes_record_present` means a record existed; `kubernetes_snapshot_valid` additionally requires usable Kubernetes content. These must not be conflated.

## 4. Formulas

Let actual workload be `y_t`, target-aligned forecast be `f_t`, oracle desired replicas be `o_t`, controller desired replicas be `d_t`, and Ready replicas be `r_t`. Let `T_f` be seconds with an aligned forecast and `T` all workload seconds.

- Forecast error: `e_t = f_t - y_t`.
- MAE: `mean(|e_t|), t in T_f`.
- RMSE: `sqrt(mean(e_t^2)), t in T_f`.
- Bias: `mean(e_t), t in T_f`.
- Transition MAE: `mean(|e_t|)` on seconds where `y_t != y_(t-1)`.
- Desired-replica error: `d_t - o_t`.
- Desired-replica MAE: `mean(|d_t - o_t|)`.
- Desired-replica bias: `mean(d_t - o_t)`.
- Deficient replica-seconds: `sum(max(o_t - d_t, 0))`.
- Excess replica-seconds: `sum(max(d_t - o_t, 0))`.
- Ready deficient replica-seconds: `sum(max(required(y_t) - r_t, 0))`, using the frozen empirical capacity lookup.
- Scale action count: `sum(1[d_t != d_(t-1)])`.
- Churn magnitude: `sum(|d_t - d_(t-1)|)`.
- Per-second failure rate: `failed_t / offered_t` when offered is positive.
- Per-second completion ratio: `completed_t / offered_t` when offered is positive.
- SLO violation: P99 latency >300 ms, failure rate >=1%, or completion ratio <99%.
- SLO violation rate: violating seconds divided by run duration.
- SLO duration: count of violating seconds.
- SLO episode: maximal contiguous sequence of violating seconds.
- Recovery time: seconds after the annotated event window until the first three consecutive SLO-healthy seconds.
- Readiness delay: seconds from a desired scale-up to the first observation where Ready replicas reach the raised desired count.
- Request P99: linear-interpolated 99th percentile of raw request latency in milliseconds.

## 5. Event construction

An event starts at each workload `transition_onset`; when absent, `peak_start` is used. It ends at the first subsequent `cycle_end`, `recovery_complete`, or `stable_end`, bounded by the next event. This yields 290 events: one per non-periodic run and five per periodic-triangle run.

Operational onset uses a preregistered 10% amplitude threshold:

`threshold = pre-event baseline + 0.10 * (actual event peak - baseline)`

Actual and predicted onset are the first actual/forecast target-time crossings of this same threshold. Timing error is predicted onset minus actual onset. A missed peak has no predicted onset rather than an invented numeric timing error.

## 6. Aligned timeline columns

| Column | Meaning |
|---|---|
| `run_id`, `source_step`, `attempt` | Accepted-run provenance. |
| `phase`, `pair_id`, `condition`, `workload_id`, `repetition`, `safety_enabled` | Experimental design fields. |
| `second`, `offset_ms` | One-second analysis key relative to T0. |
| `workload_phase`, `event_label` | Frozen workload annotations. |
| `actual_rps` | Scheduled actual workload. |
| `forecast_rps_target_aligned` | Forecast joined at its target time. |
| `forecast_error_rps` | Forecast minus actual RPS. |
| `oracle_desired_replicas` | Frozen oracle-policy command. |
| `desired_replicas` | Actual predictive/final arbitrated command. |
| `desired_replica_error` | Desired minus oracle replicas. |
| `ready_replicas`, `ready_source` | Ready count and its authoritative source. |
| `required_replicas_for_actual` | Capacity-lookup requirement for actual RPS. |
| `ready_replica_deficit` | Positive requirement minus Ready count. |
| `ready_capacity_rps` | Capacity lookup applied to Ready count. |
| `pod_created_count`, `pod_ready_transition_count` | Unique Pod events in the second; unavailable for Step 16. |
| `offered_requests`, `completed_requests`, `failed_requests` | Request counts for the second. |
| `latency_p99_ms` | Per-second request P99. |
| `failure_rate`, `completion_ratio` | Per-second SLO ratios. |
| `latency_slo_violation`, `failure_slo_violation`, `completion_slo_violation`, `any_slo_violation` | SLO flags. |
| `pod_cpu_cores`, `pod_memory_bytes`, `cpu_throttling_ratio` | Resource metrics. |
| `normalized_kubernetes_record_present` | Normalizer observed a collector record. |
| `kubernetes_snapshot_valid` | Snapshot contained usable Kubernetes evidence. |
| `pod_event_source` | Pod-event provenance or missingness reason. |

## 7. Run-level columns

Design/provenance columns retain the meanings above. Derived columns are:

| Column | Definition |
|---|---|
| `duration_seconds` | Number of workload seconds. |
| `forecast_aligned_seconds` | MAE/RMSE/bias denominator. |
| `mae_rps`, `rmse_rps`, `bias_rps`, `transition_mae_rps` | Forecast metrics from Section 4. |
| `desired_replica_mae`, `desired_replica_bias` | Replica-decision errors. |
| `deficient_replica_seconds`, `excess_replica_seconds` | Requested capacity deficit/excess versus oracle. |
| `ready_deficient_replica_seconds` | Ready deficit versus actual-workload requirement. |
| `scale_action_count`, `scale_up_action_count`, `scale_down_action_count` | Command-transition counts. |
| `churn_magnitude_replicas` | Absolute replica movement. |
| `slo_violation_seconds`, `slo_violation_rate` | SLO duration/rate. |
| `slo_episode_count`, `maximum_slo_episode_seconds` | Contiguous-episode metrics. |
| `latency_violation_seconds`, `failure_violation_seconds`, `completion_violation_seconds` | Component durations; overlaps are possible. |
| `request_count`, `request_p99_latency_ms`, `request_failure_count`, `request_failure_rate` | Request-level summaries. |
| `mean_cpu_cores`, `max_cpu_cores` | Run CPU summaries. |
| `mean_readiness_delay_seconds`, `max_readiness_delay_seconds`, `readiness_delay_observations` | Scale-up readiness summaries. |
| `pod_created_count`, `pod_ready_transition_count` | Run Pod-event totals or missing. |
| `normalized_kubernetes_record_coverage_ratio` | Fraction with collector records. |
| `kubernetes_snapshot_valid_ratio` | Fraction of raw snapshots with usable Kubernetes content. |

## 8. Event-level columns

| Column | Definition |
|---|---|
| `event_index`, `event_window_start_second`, `event_window_end_second` | Event identity and inclusive bounds. |
| `actual_onset_second`, `predicted_onset_second`, `timing_error_seconds` | Threshold-crossing onset metrics. |
| `onset_missing_reason` | Why predicted onset is missing. |
| `baseline_rps`, `onset_threshold_rps` | Threshold inputs. |
| `actual_peak_rps`, `predicted_peak_rps`, `peak_amplitude_error_rps` | Event peak metrics. |
| `mean_desired_replica_error` | Mean desired minus oracle replicas in the event. |
| `deficient_replica_seconds`, `excess_replica_seconds` | Event-local replica errors. |
| `ready_capacity_deficit_rps_seconds` | Sum of positive actual RPS minus Ready capacity. |
| `event_p99_latency_ms` | Raw-request P99 for requests sourced in the event. |
| `slo_violation_seconds`, `slo_episode_count` | Event-local SLO harm. |
| `recovery_time_seconds` | Time to three consecutive healthy seconds after event end. |
| `maximum_ready_deficit_replicas` | Largest event Ready-replica deficit. |
| `pod_event_source` | Pod-event provenance. |

## 9. Primary keys

- Aligned timeline: (`run_id`, `second`).
- Run level: (`run_id`).
- Event level: (`run_id`, `event_index`).
