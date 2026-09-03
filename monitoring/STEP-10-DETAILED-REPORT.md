# Step 10 — Observability and Experiment Data Pipeline

Version: 1.0.0  
Status: complete and live-validated  
Validated pilot: `step10-pilot-20260809-150218`  
Workload/condition: `narrow-spike-v1` / `oracle`

## 1. Purpose and result

Step 10 establishes a deterministic, versioned pipeline that reconstructs the causal path from scheduled demand, through forecast and controller decisions, Kubernetes scaling and Pod readiness, to request latency, failures, and resource utilization. The live pilot produced a continuous 180-row, one-row-per-second joined timeline and retained the higher-resolution raw evidence.

The final strengthened validator reports `valid: true`. All required forecast/controller, Kubernetes, request, application, clock, and Prometheus series are present. Checksums cover the run artifacts.

## 2. Causal data flow

1. The exact Step 7 request schedule supplies offered demand and stable request IDs.
2. The load generator dispatches each scheduled request and writes one JSON record per outcome.
3. The unchanged Step 9 controller writes one structured decision per second.
4. A Kubernetes sampler records Deployment, Pod, and EndpointSlice state every second.
5. Prometheus retains application, resource, Pod-state, and Deployment metrics.
6. Clock preflight/postflight records align the Windows runner, Docker nodes, and Prometheus.
7. The normalizer joins these sources by corrected UTC time and experiment-relative second.
8. Validation checks completeness, ordering, timing, coverage, non-empty required series, and hashes.

## 3. Collected sources

### Load generator

- Offered rate and exact scheduled dispatch time
- Actual dispatch and completion time
- Dispatch lateness and request latency
- HTTP status, timeout, error class, and response bytes
- Serving Pod name/UID and application processing duration
- Experiment, run, workload, and forecast-condition identity

### Controller

- Forecast value and horizon
- Raw and constrained replica calculations
- Previous and desired replicas
- Decision/action timestamp and reason
- Scale-down stabilization state
- API result
- Immutable policy and forecast hashes

The controller has no hidden safety net. Its logged safety state is therefore `not_applicable`/disabled.

### Kubernetes

- Deployment desired/current/updated/ready/available/unavailable replicas
- Pod identity, phase, scheduling, readiness, lifecycle timestamps, node, image, and restart state
- EndpointSlice readiness/serving/terminating state
- Kubernetes events plus final Deployment, Pod, and EndpointSlice snapshots

### Application and monitoring

- Request and error rates
- Application-internal processing histogram
- HTTP latency histogram by response code
- Pod CPU and memory
- CPU throttling ratio
- Network receive/transmit rates
- Pod readiness and restart counters
- Deployment replica, ready, and available metrics

Resource counter rates use a 60-second PromQL window because kubelet/cAdvisor is scraped more slowly than the application. The pilot demonstrated that a 10-second rate window yielded too few counter samples; the corrected window produced non-empty series without changing the underlying run.

## 4. Time synchronization

All stored event timestamps are UTC. Raw and corrected nanosecond timestamps are retained where correction is applied. The runner uses Windows Time/NTP; the pipeline independently performs five minimum-round-trip midpoint measurements against two worker nodes and Prometheus.

The pilot used measured-offset correction:

- Preflight runner correction: 39.836 ms
- Maximum corrected residual: 2.656 ms
- Preflight-to-postflight correction drift: 5.635 ms
- Allowed residual/drift: 100 ms

The control-plane `docker exec` measurement had approximately 3.1 seconds of command round-trip latency and was excluded from trusted midpoint sources. It shares the Docker VM clock with the trusted workers. The raw apparent skew remains in the report as informational evidence; corrected residual and drift are the enforcement checks.

## 5. Storage layout

Each run is stored as:

```text
results/<workload>/<forecast-condition>/<run-id>/
  inputs/
  metadata/
  raw/
    prometheus/
  normalized/
  plots/
  validation/
```

Raw events use JSON Lines, metadata and Prometheus responses use JSON, the joined analysis table uses CSV, plots use portable SVG, and integrity is recorded with SHA-256.

The layout refuses unsafe path traversal and refuses accidental reuse of an existing run directory.

## 6. Schemas and identity

Machine-readable schemas are supplied for run metadata, request records, and Kubernetes snapshots. Each run records:

- experiment ID and run ID
- workload and forecast condition
- mutation and pair-manifest identity
- controller version/image
- application image digest
- Kubernetes context, cluster version, nodes, kubelet versions, and runtimes
- random seed or explicit `not_applicable`
- T0, start, end, and capture timestamps
- SHA-256 hashes of workload, schedule, forecast, oracle, and policy inputs

## 7. Live pilot evidence

The pilot ran from T0 `2026-08-09T15:04:42.6802329Z` for 180 experiment seconds with 60 seconds of post-run recovery collection.

- Scheduled/recorded/successful requests: 5,550 / 5,550 / 5,550
- Timeouts and errors: 0 / 0
- Maximum dispatch lateness: 18.672 ms (100 ms limit)
- Controller decisions: 180, sequence 0–179
- Maximum controller timing error: 42.477 ms (250 ms limit)
- Controller catch-up intervals below 500 ms: 0
- Kubernetes snapshots: 360, collection errors: 0
- Joined timeline rows: 180
- Missing controller/Kubernetes/Prometheus seconds: 0 / 0 / 0
- Required Prometheus queries with zero samples: none

Required resource evidence after correcting the rate window:

- Pod CPU: 341 samples
- Pod memory: 338 samples
- CPU throttling ratio: 341 samples
- Network receive: 511 samples
- Network transmit: 511 samples

The separate `cpu_throttled_seconds` compatibility query returned no series in this runtime, but throttling is fully represented by the required throttled-period ratio. This optional query is retained to expose runtime capability rather than replaced with fabricated zeros.

## 8. Plots

The pipeline automatically generates:

- `workload-throughput.svg`: offered versus dispatched/completed traffic
- `replicas-readiness.svg`: controller command, Deployment desired replicas, ready Pods, and serving endpoints
- `latency-errors.svg`: P99 request latency, failures, and timeouts
- `resources.svg`: Pod CPU and throttling ratio

These are derived from the joined timeline; raw records remain authoritative.

## 9. Validation gates

The validator enforces:

- required metadata and files
- corrected clock residual and correction drift
- request presence and ID uniqueness
- dispatch lateness threshold
- controller decision presence, sequence, constant hashes, API success, timing, and no catch-up burst
- Kubernetes snapshot presence and absence of collection errors
- Prometheus export/query success
- non-zero samples for every Prometheus metric marked required in the metric catalog
- exactly ordered joined seconds and complete controller/Kubernetes/Prometheus coverage

The earlier Step 9 commissioning trace was rejected as timing evidence because it began roughly 35 seconds late and emitted a catch-up burst. The current pilot proves the corrected Step 9 controller timing: 180 normally spaced decisions and no catch-up burst.

## 10. Missing-data risks and controls

- **Clock source unavailable:** preflight fails before workload execution unless measured correction is trustworthy.
- **Slow Docker command round trips:** only sources with RTT at or below 500 ms participate in correction; all measurements remain recorded.
- **Collector process-status ambiguity:** completion is judged from snapshot coverage and stderr, while the OS status is retained separately.
- **PromQL window too short:** required-series validation now rejects zero-sample exports; resource counters use a verified 60-second window.
- **Prometheus scrape/retention loss:** raw query responses and sample counts are exported immediately after the run.
- **Controller or Pod deletion:** logs and final state are captured before cleanup.
- **Partial request output:** scheduled and recorded counts, unique IDs, errors, timeouts, and hashes expose truncation.
- **Tampering or accidental edits:** input and output SHA-256 manifests make changes detectable.

## 11. Known limitations

- CSV is the normalized portable format in v1.0.0; Parquet is not required for this experiment size.
- Kubernetes API snapshots are one-second observations, not an event watch. Pod lifecycle timestamps and Kubernetes event export retain sub-second transition evidence where Kubernetes provides it.
- Prometheus rate values inherit the source scrape interval and the selected rate window; they must not be interpreted as per-request CPU attribution.
- The control-plane midpoint measurement is diagnostic only because command latency is too high; trusted worker/Prometheus measurements govern correction.
- The pilot is commissioning evidence, not a scientific comparison run.

## 12. Completion criteria mapping

- **Pilot reconstructable second by second:** satisfied by the 180-row joined timeline with zero missing source seconds.
- **Forecast, decision, readiness, and latency align:** satisfied through common corrected UTC/T0 alignment and validated decision timing.
- **No essential timestamp missing:** satisfied in raw request, controller, Kubernetes, metadata, and clock records.
- **Run metadata automatically saved:** satisfied by the orchestrator and verified schema/required-field checks.
- **Required utilization and failure data collected:** satisfied by non-empty required Prometheus series, request outcomes, application histograms, Pod restarts, and Kubernetes events.
- **Reproducible and auditable:** satisfied by immutable inputs, versioned configuration, deterministic schedules, structured layout, tests, and SHA-256 manifests.

## 13. Final conclusion

Step 10 is complete. The pipeline can reconstruct a run from offered workload and forecast input through controller action, Deployment state, Pod readiness/serving state, request outcomes, application behavior, and resource utilization. The final live pilot and strengthened validation provide direct evidence rather than relying only on unit tests.
