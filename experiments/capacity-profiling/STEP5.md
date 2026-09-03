# Step 5 — Pod capacity profiling

## Objective

Determine a defensible safe capacity, `C_pod`, for one Ready benchmark Pod and
validate how aggregate safe capacity changes with two, three, and four replicas.
The result will map workload to replica requirements for both the predictive
controller and the oracle.

Maximum throughput is not safe capacity. `C_pod` is the highest offered request
rate that repeatedly meets every pre-registered service and capacity condition.

## Scope and scientific boundary

This campaign profiles the local kind/Docker Desktop development environment.
It validates the method and produces a local `C_pod`; it does not replace the
final native-K3s calibration required by the frozen architecture.

All kind workers share one physical laptop. Three- and four-Pod results therefore
measure empirical shared-host scaling, not independent-machine linear scaling.

## Frozen local configuration

- Application: Go benchmark service version `0.1.0`.
- Image: `anfa/benchmark-app@sha256:0fd880c5401b443a3dfb329c48fe3bd8c844643007a6097f6c31917a47961cee`.
- Work: SHA-256, `WORK_ITERATIONS=50000`, seed `anfa-benchmark-v1`.
- Pod resources: request=limit=`500m` CPU and `128Mi` memory (Guaranteed QoS).
- Placement: required affinity to `anfa.dev/role=experiment-worker`.
- Service path: Kubernetes NodePort `30080` for the external client; the documented
  local Docker-network bridge is allowed only for development.
- Readiness, liveness, and two-second termination drain behavior remain unchanged.
- Prometheus development scrape interval: 15 seconds.
- Request timeout: 10 seconds.
- Traffic model: open-loop, with offered and achieved load recorded separately.

## Pre-registered local SLO and pass rule

The provisional local request SLO is:

1. client-observed P99 latency <= 300 ms;
2. request failure rate < 1%.

A load point is capacity-valid only when it also satisfies:

3. achieved successful throughput >= 99% of offered RPS;
4. mean CPU usage <= 90% of the Pod CPU limit (`<=450m` for one Pod);
5. CPU throttling ratio < 10%; and
6. no restart, readiness loss, or unexpected replica change occurs in the
   measurement window.

Latency and failures are the SLO. Throughput fidelity, CPU, throttling, and
Kubernetes state are conservative capacity guardrails. If the pilot shows that
a guardrail is not measurable or is inappropriate, the change must be recorded
before confirmatory repetitions; completed confirmatory data must not be
reclassified after inspection.

## Experimental stages

### Stage A — Pilot and boundary location

- Force exactly one Ready Pod.
- Warm up at 25 RPS for 60 seconds; exclude warm-up observations.
- Run broad 60-second measurement points at 25, 50, 75, 100, 125, and 150 RPS.
- Allow 30 seconds recovery after each point and verify readiness/active requests.
- Use the pilot only to confirm instrumentation and locate the first failing region.

### Stage B — Single-Pod confirmatory profile

- Select 5-RPS steps spanning at least two passing and two failing points around
  the pilot boundary. Step 4 suggests 65–100 RPS as the likely region.
- Measure each point for 120 seconds after a 30-second point-specific warm-up.
- Run five independent repetitions for points within 10 RPS of the boundary and
  three repetitions for clearly safe or overloaded points.
- Alternate/rotate load-point order across repetitions to reduce thermal and
  time-order bias.
- Recover for 60 seconds between near-boundary or failing runs.
- Restart the benchmark Pod between repetition blocks, not between individual
  points, unless health checks or recovery criteria fail.

### Stage C — Multi-Pod validation

For `N` in 2, 3, and 4:

- wait until exactly `N` Pods and `N` Ready EndpointSlice endpoints exist;
- verify all Pods use the frozen image/configuration;
- test aggregate loads at approximately `0.9`, `1.0`, and `1.1` times
  `N * C_pod`;
- use three 120-second repetitions per condition;
- verify traffic reaches every Pod identity and report distribution imbalance;
- retain CPU/throttling metrics per Pod and per worker node.

## Measurements

Client-side, authoritative for the request SLO:

- scheduled/offered RPS, sent, completed, failed, and timed-out requests;
- achieved successful RPS and throughput fidelity;
- arithmetic mean latency and P50/P95/P99/max latency;
- response-code/error categories and serving-Pod counts.

Application and infrastructure, explanatory:

- received/completed/active request metrics and duration histograms;
- container CPU usage, CPU quota, throttled periods/seconds, and memory;
- Pod readiness, restart count, node placement, replica count, and EndpointSlices;
- immutable image/configuration identity and timestamps for every run.

## Capacity calculation

For offered load `r` and repetition `j`, define `pass(r,j)=1` only when all SLO
and guardrail conditions pass. A load level passes only if every required
repetition passes:

`pass_level(r) = min_j pass(r,j)`

The observed safe capacity is:

`C_pod_observed = max { r : pass_level(r)=1 }`

To avoid selecting an isolated passing point above a failure, the final boundary
must be monotonic: the selected point and all lower confirmatory points must pass.
If run-to-run variability is material, a pre-declared 5–15% safety margin will be
applied and justified:

`C_pod = floor(C_pod_observed * safety_factor)`

where `safety_factor` is in `[0.85, 1.00]` and is chosen before multi-Pod tests.

## Scaling calculation

For each replica count `N`, find the highest aggregate offered load `C_N` that
passes all repetitions. Scaling efficiency is:

`eta_N = C_N / (N * C_pod)`

If the efficiencies are acceptably stable, the local capacity formula is:

`C(N) = floor(N * C_pod * eta)`

using a conservative empirical `eta`. Otherwise, report a lookup table by replica
count and do not claim a single linear correction factor.

The controller/oracle replica conversion will be either:

`replicas = ceil(workload_rps / C_pod)`

for validated linear scaling, or the smallest `N` whose empirical `C_N` is at
least the workload for non-linear local scaling.

## Required evidence and output

- immutable run directory per execution;
- raw client request/summary results and exact parameters;
- Prometheus query results over the exact measurement window;
- Kubernetes state before and after each run;
- host, Docker, Kubernetes, image, and configuration provenance;
- per-run and aggregated CSV/JSON data;
- throughput/latency/failure/CPU/throttling curves;
- chosen `C_pod`, safety margin, scaling efficiencies, and final formula;
- Capacity Profiling Report with limitations and rejected/invalid runs disclosed.

## Completion criteria

- repeated evidence supports the single-Pod safe capacity;
- saturation onset and throughput plateau are understood;
- two-, three-, and four-Pod behavior is measured;
- workload can be converted into an oracle replica requirement;
- the selected value is conservative under observed local variability;
- the local-development result is not misrepresented as native-K3s capacity.

## Local completion result — 2026-08-03

The full local campaign is complete. The final conservative single-Pod capacity
is `C_pod=45 RPS`. Empirical aggregate capacities are `C_2=90`, `C_3=105`, and
`C_4=130 RPS`. Because efficiencies vary (`1.000`, `0.778`, and `0.722` for two,
three, and four Pods), the local controller/oracle must use the validated lookup
table rather than assume linear scaling. Detailed evidence and conclusions are
in `step5/report/STEP5_CAPACITY_PROFILING_REPORT.md`.
