# Existing instrumentation audit

## Reusable without application changes

- The Step 4 benchmark exposes request-start, completion-by-status, active-request, internal work-duration and HTTP-handler-duration metrics.
- It exposes Ready and process-start gauges plus build identity.
- Every successful response includes Pod name and UID headers and an internal `duration_ns` value.
- Step 6 established raw Deployment, Pod, ReplicaSet, EndpointSlice, Event and node capture patterns and documented Kubernetes timestamp-resolution limits.
- Step 7 provides exact per-request dispatch schedules and per-second ground truth.
- Step 8 provides complete oracle decision timelines.
- Step 9 provides per-decision structured JSON, configuration/forecast hashes and Kubernetes API acknowledgement fields.

## Gaps closed by Step 10

- The prior `loadcheck` client emitted only an aggregate summary. Step 10 adds one immutable record for every scheduled request, including planned/actual dispatch, lateness, completion, status, timeout, latency and serving Pod.
- Prometheus previously scraped every 15 seconds. The pilot temporarily uses a dedicated one-second ServiceMonitor interval and retains the raw range-query responses.
- Prior Kubernetes capture emphasized before/after snapshots. Step 10 samples Deployment, Pod and EndpointSlice state throughout the run and preserves final objects/events.
- Earlier runs did not share one schema, run identity, checksum ledger or completeness validator. Step 10 defines all four.
- Clock state was assumed or checked manually. Step 10 performs a minimum-RTT midpoint skew preflight across host, kind nodes and Prometheus.

## Cross-step issue discovered

The Step 9 commissioning evidence contains a catch-up burst: its first decision was approximately 34.97 seconds after T0 and the first 35 overdue decisions were emitted nearly instantaneously. Replica-policy equality remains valid, but that run is not valid evidence of one-second controller timing. Step 10 now rejects decision lag above 250 ms and any adjacent decision interval below 500 ms. The Step 10 pilot must therefore demonstrate a controller that is Ready before T0 and executes without catch-up.
