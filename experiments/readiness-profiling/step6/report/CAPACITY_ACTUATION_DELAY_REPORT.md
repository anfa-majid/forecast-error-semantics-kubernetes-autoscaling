# Step 6 — Capacity Actuation Delay Report

Status: local Step 6 campaign complete; native-K3s remeasurement remains required.

## Executive result

The local kind/Docker Desktop campaign completed 30 valid controlled scale-ups:
10 each for 1→2, 1→3, and 1→4 Pods. There were no main-campaign invalid
trials, timeouts, new-Pod restarts, or missing serving-Pod observations.

For the operational metric—the time from issuing the Deployment scale request
until every requested new Pod had served at least one `/work` request—the overall
distribution was:

| Statistic | Effective serving delay |
|---|---:|
| Median | 3.569 s |
| P90 | 5.219 s |
| P95 | 6.514 s |
| Maximum | 6.829 s |

Using the predeclared rule `ceil(P95 + max(2 s, 20% of P95))` gives a
**final local forecast horizon of 9 seconds**. The slowest increment's
P95 is 6.829 s (with 10 observations, conservative nearest-rank P95 equals its
maximum), which also rounds to the same 9-second horizon after the margin.

This is the final local kind/Docker Desktop Step 6 result. It must later be
remeasured on the frozen native-K3s experiment environment; the native result
will replace, not average with, this local value.

## Configuration and frozen inputs

- Kubernetes context: `kind-anfa-dev`, two kind workers on one laptop.
- Benchmark image: `anfa/benchmark-app@sha256:0fd880c5401b443a3dfb329c48fe3bd8c844643007a6097f6c31917a47961cee`.
- Image policy: `IfNotPresent`; the image was preloaded on both workers.
- Pod CPU/memory, affinity, probes, work iterations, Service, and application
  source were unchanged from Steps 4–5.
- Baseline: exactly one Ready Pod before every trial.
- Treatments: scale to 2, 3, or 4 total replicas.
- Repetitions: 10 per increment in rotated order.
- API and service observation interval: nominal 100 ms.
- Recovery: 15 seconds for main repetitions 2–10; the first validated block used
  5 seconds after successful instrumentation pilots. Order and recovery values
  are preserved in the raw records.

## Timestamp collection

The harness records forecast, decision, scale-request sent, and API-acknowledged
timestamps using UTC plus a monotonic stopwatch. Kubernetes provides Pod
creation, scheduled condition, container running, and Ready condition times. A
bounded fresh-connection HTTP probe records the first `/work` response from each
new Pod using `X-Benchmark-Pod-UID`; `X-Benchmark-Ready-At` records the
application's internal ready time.

Raw Kubernetes timestamps have whole-second resolution. They are retained for
event ordering and component diagnosis. Total creation, readiness, and
first-service delays use the harness monotonic clock because mixing whole-second
API fields with sub-second client timestamps can create small negative derived
values within the same second.

The forecast/controller timestamps are currently synthetic harness markers.
Their near-zero difference measures harness overhead, not the future production
controller's computation time. The Kubernetes actuation measurements are real.

## Results by replica increment

All values are seconds. Percentiles use the conservative nearest-rank method.
Trial readiness and service values represent the last required new Pod.

### Scale 1→2 (+1 Pod), n=10

| Metric | Median | P90 | P95 | Maximum |
|---|---:|---:|---:|---:|
| Decision-marker delay | 0.000 | 0.002 | 0.003 | 0.003 |
| Deployment API round trip | 0.156 | 0.213 | 0.265 | 0.265 |
| Pod first observed | 0.355 | 0.456 | 0.510 | 0.510 |
| Requested capacity Ready | 1.506 | 2.176 | 2.291 | 2.291 |
| Requested capacity serving | 2.755 | 3.242 | 3.248 | 3.248 |

### Scale 1→3 (+2 Pods), n=10 trials / 20 new Pods

| Metric | Median | P90 | P95 | Maximum |
|---|---:|---:|---:|---:|
| Decision-marker delay | 0.000 | 0.001 | 0.003 | 0.003 |
| Deployment API round trip | 0.154 | 0.189 | 0.201 | 0.201 |
| Per-Pod first observed | 0.378 | 0.480 | 0.483 | 0.486 |
| Requested capacity Ready | 1.868 | 2.257 | 2.270 | 2.270 |
| Requested capacity serving | 3.997 | 5.219 | 5.715 | 5.715 |

### Scale 1→4 (+3 Pods), n=10 trials / 30 new Pods

| Metric | Median | P90 | P95 | Maximum |
|---|---:|---:|---:|---:|
| Decision-marker delay | 0.000 | 0.001 | 0.003 | 0.003 |
| Deployment API round trip | 0.156 | 0.165 | 0.184 | 0.184 |
| Per-Pod first observed | 0.386 | 0.446 | 0.496 | 0.498 |
| Requested capacity Ready | 2.249 | 2.807 | 2.816 | 2.816 |
| Requested capacity serving | 4.274 | 6.514 | 6.829 | 6.829 |

## Lifecycle component interpretation

- Pod objects were first observed roughly 0.35–0.50 seconds after the request.
- Kubernetes scheduled Pods within the same whole-second timestamp in all
  recorded samples; the data supports “less than timestamp resolution,” not a
  claim of literally zero scheduler work.
- Cached container startup was usually represented as one second by Kubernetes.
  For the +3 treatment, per-Pod startup P95/maximum reached three seconds.
- Container-running to Pod-Ready was normally in the same whole-second bucket;
  some multi-Pod samples crossed one second.
- The gap between Ready and observed first service increased with the number of
  new Pods because the trial required every new backend to be sampled through
  the Service. This is operationally relevant and is why the forecast horizon is
  based on effective service rather than Ready alone.

## Image cache evidence and controlled registry comparison

All 60 new Pods in the main campaign had a matching Kubernetes event stating
that the frozen image was already present on the assigned worker. There were no
matching image-pull starts and every new Pod used the expected immutable image
ID. Thus the distribution above is explicitly a warm/pre-pulled image profile.

Because the frozen local image had originally been loaded directly into kind, a
temporary registry was created on the isolated kind network. A separate
zero-replica treatment Deployment used the identical benchmark binary and
configuration, was pinned to the otherwise idle worker, and was scaled 0→1.
Before each repetition, its benchmark image reference was removed and absence
was verified. Ten repetitions were retained; the first registry-use pilot was
excluded from the distribution.

| +1 Pod treatment | Median Ready | P95 Ready | Median first service | P95 first service |
|---|---:|---:|---:|---:|
| Pre-pulled (`n=10`) | 1.506 s | 2.291 s | 2.755 s | 3.248 s |
| Registry repull (`n=10`) | 2.403 s | 2.513 s | 3.895 s | 4.553 s |

The registry-repull P95 effective delay was 1.305 seconds higher than the
pre-pulled +1-Pod P95. Kubernetes recorded a pull-duration median of 1.236
seconds and P95/maximum of 1.310 seconds, closely matching the effective-delay
increase. The excluded first-use pilot reached 7.344 seconds Ready and 8.772
seconds effective service because pulling did not begin until roughly six
seconds after scheduling.

Containerd may retain reusable layer content after an image reference is
removed, so the 10-repetition treatment is accurately described as
**image-reference absent / local-registry repull**, not a remote-registry or
fully empty content-store experiment. It is nevertheless sufficient to show
that allowing image resolution/pulling adds delay and variability. The final
decision is to **pre-pull the immutable image on every experiment worker** and
verify it before the main campaign. The native-K3s image distribution method
must be tested before considering `imagePullPolicy: Never`; the frozen manifest
therefore remains `IfNotPresent`.

## Instrumentation corrections and exclusions

- The first pilot correctly failed because the NodePort bridge had been stopped.
- One pilot was invalidated by overlap with a second baseline-reset process.
- PowerShell's pooled HTTP client could pin probes to one backend and could exceed
  its timeout. It was replaced before the main campaign by bounded `curl`
  probes using fresh connections.
- Whole-second Kubernetes timestamps initially produced a negative creation
  difference. The method was corrected before the main campaign to use monotonic
  first-observation elapsed time for end-to-end values while preserving raw API
  fields.
- All `instrumentation-pilot*` directories are excluded from the main analysis.
  No main result was removed or reclassified.
- The registry first-use repetition (`rep00`) is disclosed but excluded from the
  10-repetition repull distribution.
- Cleanup restarted containerd after all measurements, increasing the surviving
  baseline Pod's later restart count. Those post-campaign restarts are not part
  of any retained trial window.

## Limitations

- All kind nodes share one physical Windows/WSL2/Docker Desktop host.
- The local NodePort/socat bridge adds a development-only request path.
- A 100 ms requested polling interval is an upper-bound parameter; invoking
  `kubectl` and the HTTP request adds processing time, visible in raw RTT fields.
- Kubernetes condition timestamps limit fine-grained component precision.
- First-service time includes Service load-balancing sampling time and therefore
  grows with the number of new backends; this is intentional for the operational
  horizon but should be distinguished from readiness-probe completion.
- The actual predictive controller has not yet replaced the synthetic marker.
- Ten observations per increment make nearest-rank P95 equal to the maximum;
  additional repetitions would improve tail estimation.

## Current completion assessment

| Requirement | Status |
|---|---|
| Timestamp method defined and raw evidence preserved | Complete |
| +1, +2, +3 controlled scale-ups | Complete |
| Median/P90/P95/maximum reported | Complete |
| Readiness delay measured | Complete for local environment |
| First-service delay measured | Complete for local environment |
| Cached image behaviour verified | Complete |
| Controlled registry-repull comparison | Complete |
| Image policy decision | Complete: pre-pull immutable image on every worker |
| Forecast horizon tied to measured delay | Complete: 9 s local horizon |
| Native-K3s remeasurement | Required before main research campaign |
