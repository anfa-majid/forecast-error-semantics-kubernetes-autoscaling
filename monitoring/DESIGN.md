# Frozen Step 10 design contract

## Causal chain

`workload schedule → request dispatch/outcome → forecast → controller decision/API action → Deployment desired state → Pod lifecycle/Ready → EndpointSlice serving → utilization → latency/errors`

## Time contract

- UTC RFC3339 timestamps and epoch nanoseconds are retained where available.
- Load generation and controller decisions use offsets from one immutable T0.
- Per-process durations use monotonic clocks.
- Kubernetes source timestamps and collector observation timestamps are both retained.
- Preflight maximum absolute clock skew is 100 ms.
- Controller absolute decision lag is limited to 250 ms; catch-up bursts are invalid.
- Raw measurements are never interpolated and presented as observations.

## Resolution

- Request/controller events: native event resolution.
- Joined analysis: one row per second.
- Kubernetes state: one-second polling plus final Kubernetes Events.
- Prometheus: one-second evaluation over one-second scrape data for experiment targets.
- Existing whole-second Kubernetes condition timestamps remain explicitly lower precision.

## Storage

Raw JSON/JSONL responses are immutable evidence. CSV is used for normalized analysis tables, JSON for metadata/validation, SVG for reproducible plots, and SHA-256 for integrity. Parquet can be added as a derived optimization but cannot replace readable canonical evidence.

## Validity

A run is invalid or incomplete if required identity, clock, request, controller, Kubernetes, Prometheus or joined-timeline evidence is absent; if request/decision sequences are broken; if timing limits fail; if API/collector errors occur; or if required second-level coverage is missing.
