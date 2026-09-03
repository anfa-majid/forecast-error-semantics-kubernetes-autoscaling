# Step 6 — Kubernetes actuation and readiness delay

## Objective

Measure the elapsed time between a forecast signal, a scaling action, and usable
serving capacity. The result selects the forecast horizon from an observed delay
distribution rather than an assumed Pod startup time.

## Frozen inputs from Steps 1–5

- Local environment: `kind-anfa-dev` on Docker Desktop/WSL2.
- Application image and digest remain unchanged from Step 5.
- Work intensity, probes, resources, placement, Service, and Pod template remain
  unchanged.
- Step 5 capacity remains `C_pod=45 RPS`, with the empirical local capacity table
  `C_1=45`, `C_2=90`, `C_3=105`, and `C_4=130 RPS`.
- This is a local-development actuation profile. The final native-K3s environment
  must be measured again.

## Timestamp model

Every trial records UTC RFC3339 timestamps and preserves raw Kubernetes objects.

| Symbol | Event | Authority |
|---|---|---|
| `t_forecast` | synthetic forecast becomes available | runner clock |
| `t_decision` | controller selects desired replicas | runner clock |
| `t_scale_sent` | Deployment scale request is issued | runner clock |
| `t_scale_ack` | Kubernetes API acknowledges the update | runner clock |
| `t_created` | new Pod object created | Pod `metadata.creationTimestamp` |
| `t_scheduled` | PodScheduled becomes True | condition `lastTransitionTime` |
| `t_started` | application container starts | `state.running.startedAt` |
| `t_ready` | Pod Ready becomes True | condition `lastTransitionTime` |
| `t_app_ready` | application internally enables readiness | `X-Benchmark-Ready-At` |
| `t_first_request` | client first observes `/work` served by the new Pod | runner clock plus Pod identity header |

Kubernetes lifecycle timestamps normally have one-second resolution. They are
retained for authoritative ordering, but can produce small negative differences
when subtracted from a millisecond-scale client timestamp in the same second.
Therefore, total creation/readiness/first-service delays use the runner's
monotonic first-observation clock; raw API-derived differences are retained as
diagnostic fields. First-service timing is bounded by the request probe interval
and network round-trip time; both are recorded.

## Delay definitions

- Decision delay: `t_decision - t_forecast`.
- Deployment/API delay: `t_scale_ack - t_scale_sent`.
- Pod creation delay: `t_created - t_scale_sent`.
- Scheduling delay: `t_scheduled - t_created`.
- Startup delay: `t_started - t_scheduled`.
- Container-to-Ready delay: `t_ready - t_started`.
- Readiness actuation delay: `t_ready - t_scale_sent`.
- Effective serving delay: `t_first_request - t_scale_sent`.
- Increment completion delay: the maximum readiness/effective-serving delay
  among all new Pods in a trial, because the requested capacity is not fully
  available until the last required Pod is usable.

Until the research controller is implemented, the forecast and decision markers
are emitted by the experimental harness. Their difference measures harness
overhead, not production controller computation time. The Deployment-to-service
measurements remain real Kubernetes observations; the same marker interface must
later be connected to the actual controller.

## Experimental design

1. Establish exactly one Ready baseline Pod and capture its UID.
2. Wait for a quiet recovery interval.
3. Emit the forecast and decision markers.
4. Scale from one Pod to 2, 3, or 4 Pods (`+1`, `+2`, `+3`).
5. Poll the Kubernetes API at 100 ms and `/work` at 10 RPS until every newly
   created Pod is Ready and has served at least one request.
6. Preserve raw Pods, Deployment, ReplicaSet, EndpointSlice, Event, and node
   objects, plus the normalized trial record.
7. Scale back to one Pod, wait for completion, and recover before the next trial.

Use at least 10 valid repetitions per increment for the main local report. Rotate
increment order between blocks to reduce time/temperature bias. Mark a trial
invalid rather than silently repairing it if the baseline is wrong, unrelated
rollout occurs, a Pod restarts, a timestamp is missing, or the timeout expires.

## Cache experiment

The main campaign uses pre-pulled images (`IfNotPresent`) to isolate ordinary
Kubernetes actuation from registry/network variability. The final native-K3s
environment must validate its image distribution method before considering a
stricter `Never` policy. Record each Pod's
container waiting reason and image ID. A separate cold-image treatment may be
run only with a controlled removable image/tag and a documented registry path;
it must not mutate or relabel the frozen benchmark image. Compare cached and
uncached distributions separately and do not pool them.

## Forecast-horizon rule

Compute median, P90, P95, and maximum for trial-level effective serving delay.
The preferred local horizon is:

`H = ceil(P95 effective-serving delay + measurement uncertainty + safety margin)`

The safety margin is declared before inspecting the final distribution (default
20% of P95, with a minimum of two seconds). The horizon must cover the slowest
replica increment the predictive controller will request. Readiness P95 is also
reported, but effective-serving P95 is the operational selection metric.

## Outputs

- immutable raw directory per trial;
- normalized per-Pod and per-trial CSV/JSON;
- median/P90/P95/maximum delay tables;
- cached-image evidence and any separate cold-image comparison;
- selected forecast horizon with calculation and limitations;
- Capacity Actuation Delay Report.
