# Step 10 - Observability and Experiment Logging Pipeline

Status: implementation, offline verification, live pilot, and completeness validation complete  
Version: `1.0.0`  
Validated pilot: `step10-pilot-20260809-150218`  
Pilot workload: `narrow-spike-v1`  
Pilot forecast condition: `oracle`

## Executive result

Step 10 implements the complete observability and experiment-data pipeline required to reconstruct the autoscaling causal chain. It preserves the intended workload, actual request dispatch, forecast-driven controller decisions, Kubernetes replica state, Pod lifecycle and serving readiness, request outcomes, application processing, resource utilization, clock evidence, run metadata, normalized analysis data, plots, validation results, and cryptographic checksums.

The final live pilot passed all mandatory checks. It contains 5,550 unique request records, 180 normally timed controller decisions, 360 one-second Kubernetes snapshots, non-empty required Prometheus series, and a 180-row second-by-second joined timeline with no missing controller, Kubernetes, or Prometheus seconds. Ten offline unit tests pass. The final validator reports `valid: true` with zero failed error-severity checks.

This pipeline is now the required data path for later experimental runs. It does not change the workload, forecast, autoscaling policy, or application. Its role is observation, provenance, alignment, validation, and reproducible export.

## Purpose and research role

The research question depends on a chain of events rather than a single endpoint measurement:

```text
offered workload
  -> forecast supplied to the fixed controller
  -> desired replica calculation
  -> Kubernetes scale command
  -> Deployment and Pod lifecycle
  -> Ready and serving capacity
  -> completed requests, latency and failures
  -> resource utilization and throttling
```

If any link is missing or timestamped inconsistently, later analysis could incorrectly attribute latency or failures to forecast error. Step 10 therefore preserves both raw evidence and a joined analysis view. Raw records remain authoritative; normalization never replaces them.

## Design principles

The implementation follows these fixed principles:

1. **UTC everywhere.** Human-readable timestamps use UTC and high-resolution numeric timestamps are retained.
2. **Raw before derived.** Every source is archived before normalization or plotting.
3. **Stable identities.** Experiment, run, workload, forecast condition, controller, mutation, and input identities are recorded.
4. **One immutable run directory.** A run directory cannot be silently reused.
5. **Complete no-op logging.** Controller decisions are preserved even when no scale write occurs.
6. **Desired is not Ready.** Controller command, Deployment desired state, Pod readiness, and serving endpoints remain distinct.
7. **Fail closed on missing evidence.** Required files, sources, time coverage, hashes, and Prometheus series are validated.
8. **No fabricated zeros.** An unavailable optional metric remains visibly empty rather than being replaced by a misleading zero.
9. **Reversible commissioning changes.** Temporary scrape changes and controller resources are restored or removed in cleanup.
10. **Versioned contracts.** Configuration, schemas, queries, code, report, and pilot evidence are packaged together.

## Frozen pipeline configuration

| Parameter | Value | Purpose |
|---|---:|---|
| Schema/package version | 1.0.0 | Versioned interpretation contract |
| Primary sample interval | 1,000 ms | Second-by-second causal reconstruction |
| Kubernetes polling interval | 1,000 ms | Deployment, Pod, and endpoint state |
| Prometheus export step | 1 second | Common analysis grid |
| Pre-run monitoring window | 30 seconds | Stable baseline and startup context |
| Post-run monitoring window | 60 seconds | Readiness and recovery observation |
| Request timeout | 10 seconds | Explicit timeout classification |
| Maximum corrected clock residual | 100 ms | Cross-source time validity |
| Maximum dispatch lateness | 100 ms | Workload fidelity gate |
| Maximum tolerated consecutive missing seconds | 1 | Missing-data policy |
| Namespace | `default` | Benchmark/controller scope |
| Target Deployment/Service | `benchmark-app` | Application under test |
| Application container | `benchmark-app` | Resource metric selector |
| Controller selector | `app.kubernetes.io/name=predictive-autoscaler` | Controller evidence |
| Safety net | disabled / not applicable | Matches fixed Step 9 design |

The pilot temporarily changed only the benchmark application's ServiceMonitor interval from 15 seconds to 1 second. The script restored the 15-second interval in `finally`. Kubelet/cAdvisor retained its slower scrape interval, so resource counter rates use a verified 60-second PromQL range.

## End-to-end execution sequence

The commissioning/orchestration script performs the following sequence:

1. confirms the expected Kubernetes context and cluster availability;
2. captures Docker and node metadata;
3. starts a local Prometheus port-forward;
4. records the exact temporary ServiceMonitor manifest and applies one-second application scraping;
5. creates a unique run directory and copies all authoritative inputs;
6. performs clock preflight measurement and derives the runner correction;
7. creates unique immutable runtime and forecast ConfigMaps;
8. renders and archives the exact Step 9 controller Deployment manifest;
9. starts the Kubernetes sampler before T0;
10. starts the controller and verifies that it becomes Ready before T0;
11. executes the exact Step 7 per-request schedule;
12. observes the 60-second post-workload recovery window;
13. verifies Kubernetes snapshot coverage and collector stderr;
14. captures controller logs, application logs, Kubernetes events, and final objects;
15. exports all Prometheus queries for the common time range;
16. performs clock postflight measurement;
17. captures run metadata and input hashes;
18. creates the 180-row joined timeline and SVG plots;
19. runs completeness/timing/coverage validation;
20. generates SHA-256 checksums; and
21. restores monitoring configuration, removes the temporary controller, and returns the benchmark to one replica.

## Data-source contracts

### 1. Workload schedule and load generator

The Step 7 request schedule is authoritative for offered workload. Each scheduled request has a stable request ID, experiment-relative offset, source second, target RPS, and number of requests scheduled in that second.

Each load-generator JSONL record contains:

| Field group | Principal fields |
|---|---|
| Identity | `experiment_id`, `run_id`, `workload_id`, `forecast_condition`, `request_id` |
| Intended timing | `t0_utc`, `scheduled_utc`, `scheduled_epoch_ns`, `scheduled_offset_us` |
| Actual timing | raw/corrected dispatch and completion epoch ns, dispatch/completion offsets |
| Fidelity | `dispatch_lateness_us`, `target_rps`, `scheduled_requests_in_second` |
| Outcome | status code, success, timeout, error class/message, response bytes |
| Latency | end-to-end `latency_us` |
| Serving identity | Pod name and UID from application response headers |
| Application processing | `application_duration_ns` from the benchmark response |

The generator logs every completion path, including HTTP errors, network errors, and timeouts. The summary checks scheduled versus recorded counts, successful completions, timeouts, errors, maximum dispatch lateness, schedule hash, output hash, and true first-dispatch/last-completion timestamps.

### 2. Predictive controller

The Step 9 JSONL decision log is preserved without transformation. Every experimental second includes:

- decision sequence and tick offset;
- UTC timestamp and monotonic elapsed time;
- workload, condition, mutation, and pair-manifest identity;
- forecast issue/target time, horizon, and predicted RPS;
- safety-adjusted workload;
- raw, bounded, stabilized, previous, and commanded replicas;
- scale action, reason, and scale-down-held state;
- policy and forecast SHA-256 hashes;
- Kubernetes API request/response timing and outcome; and
- structured error information.

The pipeline verifies consecutive sequence values, constant policy/forecast hashes, absence of API failures, timing relative to T0, and absence of catch-up bursts. It does not infer readiness from a successful scale write.

### 3. Kubernetes state

The sampler makes one observation per second and records:

| Object | Recorded state |
|---|---|
| Deployment | desired, current, updated, ready, available, unavailable, generation and resource version |
| Pod | name, UID, creation/deletion, node, phase, IP, scheduling, readiness, container readiness, restart count, image, container ID, running start, previous termination |
| EndpointSlice endpoint | slice, address, Pod name/UID, node, ready, serving, terminating |

Each observation stores raw and corrected observation time, experiment elapsed time, collection duration, and any collection error. The script also exports Kubernetes Events and final Deployment, Pod, and EndpointSlice objects.

EndpointSlice serving state is important: Pod Ready and traffic-serving capacity can differ briefly during startup or termination. Both remain separate in the joined timeline.

### 4. Application telemetry

The benchmark application exposes:

- total work requests;
- completed requests grouped by status;
- active requests;
- internal processing-time histogram;
- HTTP request-duration histogram;
- readiness, startup, and build information; and
- Pod identity and internal duration response headers.

Per-request response evidence and Prometheus aggregates provide independent views of request outcomes and processing time.

### 5. Prometheus and infrastructure telemetry

| Query ID | Meaning | Required |
|---|---|---|
| `application_requests` | application request rate by Pod | Yes |
| `application_errors` | non-2xx completion rate | Yes |
| `application_internal_duration` | internal duration histogram | Yes |
| `application_http_duration` | HTTP latency histogram by Pod/code | Yes |
| `pod_cpu` | CPU cores by application Pod | Yes |
| `pod_memory` | working-set bytes by application Pod | Yes |
| `cpu_throttling_ratio` | throttled periods / total periods | Yes |
| `cpu_throttled_seconds` | runtime compatibility metric | No |
| `network_receive` | received bytes/s by application Pod | Yes |
| `network_transmit` | transmitted bytes/s by application Pod | Yes |
| `pod_ready` | readiness state by Pod | Supporting |
| `pod_restarts` | restart count by Pod/container | Supporting |
| Deployment queries | desired/current-ready/available state | Supporting |

Application rate/histogram queries use a 10-second window because the application is scraped every second during the run. cAdvisor counter queries use a 60-second window so that the slower source contains enough points for `rate()`.

## Clock synchronization and correction

Windows Time was configured to use multiple NTP peers and reported synchronized state before the successful pilot. The pipeline still performs an independent run-level measurement because system-service status alone does not quantify cross-source alignment.

For each source it takes five samples. For a sample with local send time `t1`, remote time `tr`, and local receive time `t2`:

```text
midpoint = (t1 + t2) / 2
observed offset = tr - midpoint
round-trip time = t2 - t1
```

The lowest-RTT sample represents each source. Only sources with RTT at or below 500 ms are trusted for correction. The median trusted offset becomes the runner correction. Raw timestamps, corrected timestamps, every attempt, trusted-source list, residual, mode, and pass/fail result are retained.

Pilot clock evidence:

| Measurement | Result |
|---|---:|
| Preflight runner correction | +39.836 ms |
| Maximum corrected residual | 2.656 ms |
| Postflight runner correction | +34.201 ms |
| Correction drift | 5.635 ms |
| Enforcement limit | 100 ms |
| Trusted sources | worker, worker2, Prometheus |

The control-plane measurement showed approximately 3.1 seconds of command RTT. It was excluded from correction but retained as informational evidence. The raw 1.53-second apparent skew is therefore not treated as a clock failure; it is dominated by measurement transport. The trusted worker and Prometheus measurements establish alignment.

## Run identity and provenance

The run metadata schema requires:

- schema version;
- experiment and run IDs;
- workload and forecast condition;
- controller version and image;
- application image digest;
- Kubernetes context and cluster version;
- random seed or explicit `not_applicable`;
- T0, start, end, capture time, and run status.

The implementation additionally records mutation ID, pair-manifest ID, namespace, Deployment, host platform, Python version, nodes, kubelet versions, container runtimes, OS images, application pull policy, and SHA-256 hashes for the workload, request schedule, forecast, oracle timeline, and frozen policy.

Pilot provenance includes:

| Item | Value |
|---|---|
| Kubernetes context | `kind-anfa-dev` |
| Kubernetes/kubelet version | v1.36.1 |
| Nodes | one control plane and two workers |
| Container runtime | containerd 2.3.1 |
| Controller image | `anfa/predictive-autoscaler:1.0.0` |
| Application digest | `sha256:0fd880c5401b443a3dfb329c48fe3bd8c844643007a6097f6c31917a47961cee` |
| Random seed | `not_applicable` |
| Run status | `commissioning_only` |

## Directory and storage contract

```text
results/<workload-id>/<forecast-condition>/<run-id>/
  inputs/
    authoritative workload, schedule, forecast, oracle and policy
    rendered-manifests/
  metadata/
    run-metadata.json
    clock-preflight.json
    clock-postflight.json
    cluster and collector evidence
  raw/
    load-generator-requests.jsonl
    controller.jsonl
    kubernetes-snapshots.jsonl
    kubernetes-events.json
    application.log
    final Kubernetes objects
    prometheus/
  normalized/
    joined-timeline.csv
  plots/
    workload-throughput.svg
    replicas-readiness.svg
    latency-errors.svg
    resources.svg
  validation/
    completeness-report.json
    checksums.sha256
```

JSON Lines is used for high-cardinality event streams. JSON is used for metadata, Kubernetes exports, and exact Prometheus API responses. CSV is used for the compact analysis table. SVG is used for dependency-free plots. Parquet is not necessary at the present run size but can be added later without changing raw contracts.

## Normalized one-second timeline

For each experiment second `0..179`, the normalizer joins:

- offered RPS and workload event label;
- scheduled, dispatched, completed, failed, and timed-out requests;
- mean/P50/P95/P99/max latency and maximum dispatch lateness;
- forecast, raw/bounded/stabilized requirement, prior command, command, action, and API result;
- Deployment desired/current/ready/available replicas;
- Ready Pod count, serving endpoint count, and restart count;
- CPU, memory, throttling ratio, receive/transmit rate;
- application request and error rates; and
- Boolean presence flags for controller, Kubernetes, and Prometheus evidence.

Request records are bucketed by experiment-relative scheduled/dispatch timing. Kubernetes observations are aligned to T0 and the most recent valid state is carried only as state semantics require. Prometheus samples use their source timestamps. Presence flags prevent carried state from hiding missing observations.

## Automated plots

| Plot | Series | Interpretation |
|---|---|---|
| Workload and throughput | offered, dispatched, completed | workload fidelity and completion deficit |
| Replicas and readiness | command, Deployment desired, Ready Pods, serving endpoints | decision-to-capacity delay |
| Latency and failures | P99, failed requests, timeouts | user-visible consequence |
| Resources | CPU cores and throttling ratio | saturation/throttling evidence |

The SVGs are review aids. Quantitative analysis must use the normalized CSV or raw records, not values estimated visually from the plot.

## Validation contract

The completeness validator enforces 25 run checks. Error-severity checks must all pass.

### Metadata and clocks

- all required metadata fields exist;
- measured correction mode passes;
- corrected residual is at or below 100 ms;
- preflight/postflight correction drift is at or below 100 ms;
- raw high-latency control-plane skew remains informational.

### Workload delivery

- request records exist;
- request IDs are unique;
- maximum dispatch lateness is at or below 100 ms.

### Controller

- decisions exist and sequences are consecutive;
- no Kubernetes API errors occurred;
- one policy hash and one forecast hash are used;
- every decision is within 250 ms of its scheduled tick;
- no adjacent decisions form a catch-up burst below 500 ms.

### Kubernetes

- snapshots exist;
- no snapshot contains a collection error;
- collector evidence covers at least 95% of the planned window and stderr is empty.

### Prometheus

- export exists and contains no query errors;
- every query marked required in `metric-catalog.json` has at least one sample;
- optional unsupported metrics remain visible but do not invalidate a run when an equivalent required measure exists.

### Joined reconstruction

- timeline exists and seconds are exactly consecutive;
- controller, Kubernetes, and Prometheus coverage have zero missing experiment seconds;
- all mandatory evidence files exist.

## Offline test coverage

Ten unit tests pass:

- Prometheus scalar clock responses are accepted;
- Kubernetes Deployment replica dimensions remain distinct;
- Pod lifecycle and endpoint conditions are transformed correctly;
- complete run layout is created and existing runs are refused;
- path traversal is rejected;
- authoritative request schedule loads correctly;
- duplicate and unordered schedule entries are rejected;
- nanosecond summary timestamps convert correctly to UTC;
- joined causal timeline construction works; and
- percentile calculation is correct.

Python compilation and PowerShell script parsing also pass.

## Live pilot results

Evidence directory: `results/narrow-spike-v1/oracle/step10-pilot-20260809-150218`

| Measure | Observed | Gate/result |
|---|---:|---|
| Experiment duration | 180 s | Complete |
| Post-run observation | 60 s | Complete |
| Requests scheduled | 5,550 | Reference |
| Requests recorded | 5,550 | Exact match |
| Successful requests | 5,550 | Complete |
| Errors | 0 | Pass |
| Timeouts | 0 | Pass |
| Maximum dispatch lateness | 18.672 ms | <=100 ms |
| Controller decisions | 180 | Exact |
| Decision sequence | 0-179 | Consecutive |
| Maximum controller lag | 42.477 ms | <=250 ms |
| Catch-up intervals | 0 | Pass |
| Scale-up actions | 1 | Observed |
| Scale-down actions | 3 | Observed |
| No-op decisions | 176 | Observed |
| Kubernetes snapshots | 360 | Complete |
| Kubernetes collection errors | 0 | Pass |
| Joined rows | 180 | Exact |
| Missing controller seconds | 0 | Pass |
| Missing Kubernetes seconds | 0 | Pass |
| Missing Prometheus seconds | 0 | Pass |
| Failed mandatory validator checks | 0 | Pass |

Resource/application exports include:

| Metric | Series | Samples |
|---|---:|---:|
| Application requests | 2 | 338 |
| Application errors | 1 | 271 |
| Internal-duration histogram | 28 | 4,732 |
| HTTP-duration histogram | 28 | 4,718 |
| Pod CPU | 2 | 341 |
| Pod memory | 2 | 338 |
| CPU throttling ratio | 2 | 341 |
| Network receive | 4 | 511 |
| Network transmit | 4 | 511 |
| Pod Ready | 4 | 466 |
| Pod restarts | 4 | 466 |
| Deployment desired/ready/available | 1 each | 271 each |

The `cpu_throttled_seconds` compatibility metric returned no series on this runtime. This does not remove CPU-throttling observability because the required throttled-period ratio contains 341 samples and is the frozen analysis measure.

## Defects discovered and corrected

Commissioning intentionally exposed integration defects before scientific runs:

1. **Windows was initially unsynchronized.** Windows Time was configured with multiple NTP peers and synchronized; the pipeline still performs independent run-level clock measurement.
2. **Docker Desktop restart removed the original kind host API binding.** A local bridge and explicit temporary kubeconfig restored cluster access without changing experiment state.
3. **A workload path containing spaces was split by `Start-Process`.** The authoritative schedule is now copied into the run input directory before generator launch.
4. **Kubernetes collector process status was unreliable in PowerShell.** Acceptance now checks actual snapshot count and stderr while retaining the OS exit code as audit metadata.
5. **Initial PromQL counter windows were too short.** Ten seconds contained too few cAdvisor samples; verified 60-second windows now produce CPU, throttling, and network data.
6. **The first validator accepted empty required metric series.** It now derives required Prometheus queries from the metric catalog and rejects any zero-sample required series.
7. **Load summary `started_utc` was written at completion.** It now derives start/end from first dispatch and last completion; a regression test covers nanosecond-to-UTC conversion.
8. **Old Step 9 commissioning timing was invalid.** Step 10 audit detected approximately 35 seconds of lateness and a catch-up burst. The successful Step 10 pilot demonstrates corrected controller timing with 180 normally spaced decisions.

Failed commissioning attempts are retained only as debugging evidence. They are not scientific observations and must not enter the experimental analysis dataset.

## Reproducibility procedure

Prerequisites:

- Docker Desktop and the `kind-anfa-dev` cluster running;
- benchmark application and monitoring stack healthy;
- synchronized Windows clock;
- explicit Step 10 kubeconfig where required;
- authoritative Step 7, Step 8, and Step 9 artifacts unchanged.

The end-to-end command is:

```powershell
$env:KUBECONFIG = "<path-to-kubeconfig>"

& ".\scripts\run-step10-local-pilot.ps1" `
  -Python "python"
```

The script prints `STEP 10 PILOT PASSED` only after normalization, plots, all validation gates, and checksums succeed. A new unique run directory is created every time.

## Missing-data risks and controls

| Risk | Detection/control |
|---|---|
| NTP unavailable or excessive clock error | clock preflight fails before workload |
| Offset changes during run | postflight drift gate |
| High-latency time probe | RTT trust threshold; attempts retained |
| Partial workload execution | scheduled/recorded counts, IDs, outcomes, hashes |
| Dispatch scheduler overload | per-request lateness and maximum-lateness gate |
| Controller starts late | absolute decision timing and catch-up-burst gates |
| Controller/Kubernetes API failure | structured API result and fatal run validation |
| Sampler termination | planned coverage, row count, stderr, per-record error |
| Readiness mistaken for desired count | separate Deployment, Pod, and endpoint series |
| Prometheus query syntactically succeeds but is empty | required-series sample-count gate |
| Scrape gap | joined presence coverage and raw export counts |
| Mutable input | copied inputs and SHA-256 provenance |
| Cleanup deletes evidence | logs/final objects captured before cleanup |
| Accidental output modification | run checksum manifest and package archive digest |

## Known limitations and interpretation constraints

- The commissioning environment is local kind/Docker Desktop; final campaign runs must repeat preflight and capture their own environment metadata.
- Kubernetes state is polled every second rather than consumed through an API watch. Native lifecycle timestamps and Events supplement this resolution.
- Prometheus counter rates reflect scrape interval and range-window smoothing. They are operational utilization measures, not per-request attribution.
- The normalized v1.0.0 table is CSV. Raw sources permit future Parquet conversion without loss.
- The control-plane time probe is diagnostic because its command RTT is high; worker and Prometheus sources govern correction.
- Optional `cpu_throttled_seconds` is unavailable on the current runtime; required throttling ratio is available and validated.
- Application logs are supplemental because per-request records and Prometheus metrics carry the primary outcome evidence.
- The successful pilot is commissioning evidence and must not be mixed with replicated scientific-condition runs.

## File and component inventory

| Path/component | Responsibility |
|---|---|
| `configuration/pipeline-config.json` | fixed intervals, limits, selectors, and safety state |
| `configuration/metric-catalog.json` | required metrics and units |
| `configuration/prometheus-queries.json` | frozen PromQL export definitions |
| `schemas/` | machine-readable metadata/request/Kubernetes contracts |
| `src/anfa_observability/loadgen.py` | deterministic schedule execution and per-request logging |
| `clock.py` | midpoint clock measurement and correction evidence |
| `kubernetes.py` | Deployment/Pod/EndpointSlice sampler |
| `prometheus.py` | raw query-range export and sample counts |
| `metadata.py` | environment, image, cluster, input-hash capture |
| `normalize.py` | one-second causal join |
| `plots.py` | portable SVG evidence plots |
| `validate.py` | completeness, timing, coverage, and required-series gates |
| `checksums.py` | SHA-256 run integrity manifest |
| `layout.py` | safe immutable run-directory structure |
| `scripts/run-step10-local-pilot.ps1` | end-to-end orchestration and reversible cleanup |
| `tests/` | offline contract and transformation tests |
| `AUDIT.md` | preimplementation instrumentation audit |
| `DESIGN.md` | concise design contract |
| `STEP-10-DETAILED-REPORT.md` | completion report |
| `STEP10.md` | canonical full Step 10 research document |

## Completion assessment

| Written Step 10 requirement | Evidence | Status |
|---|---|---|
| Offered request rate | exact Step 7 schedule and normalized offered RPS | Complete |
| Completed requests | 5,550 per-request outcomes and aggregate series | Complete |
| Latency | per-request microseconds, percentiles, HTTP histogram | Complete |
| Status codes and timeouts | explicit per-request fields; zero lost outcomes | Complete |
| Forecast input | complete Step 9 decision records | Complete |
| Desired replicas and action time | 180 controller records | Complete |
| Action reason and safety state | logged action/reason; safety disabled/not applicable | Complete |
| Kubernetes desired/current/available/ready | sampler plus Prometheus series | Complete |
| Pod lifecycle and restarts | Pod state, events, Ready transitions, restart counters | Complete |
| Application request count | Prometheus application series | Complete |
| Internal processing time | response duration and histogram | Complete |
| Application errors | per-request plus Prometheus non-2xx rate | Complete |
| CPU and memory | non-empty Pod series | Complete |
| CPU throttling | non-empty throttling-ratio series | Complete |
| Network | non-empty receive/transmit series | Complete |
| Latency histogram | non-empty HTTP histogram | Complete |
| Synchronized clocks | NTP plus pre/post measured correction | Complete |
| UTC millisecond-or-better timestamps | UTC plus epoch nanoseconds/microseconds | Complete |
| Common experiment marker | T0 stored across identities and sources | Complete |
| Run metadata | automatically generated schema-compliant JSON | Complete |
| Structured directory | safe workload/condition/run layout | Complete |
| Raw Prometheus export | exact JSON query responses and summary | Complete |
| CSV experiment events | 180-row joined timeline | Complete |
| Sample plots | four SVG plots | Complete |
| Missing-data checks | 25-check completeness validator | Complete |
| Pilot reconstructable second by second | zero missing source seconds | Complete |
| Forecast/decision/readiness/latency alignment | corrected UTC/T0 join and timing gates | Complete |
| Reproducibility | immutable inputs, schemas, hashes, tests, run script | Complete |

## Final conclusion

Step 10 is complete. The versioned pipeline captures every required stage of the experimental causal chain and has been proven in a live narrow-spike oracle pilot. The complete raw evidence, normalized timeline, plots, metadata, validation report, checksums, source code, tests, and operational procedure are retained. Future forecast-error experiments can now be evaluated with a consistent and auditable observability contract.
