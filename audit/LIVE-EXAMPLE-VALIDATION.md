# Live functional-example validation

Validation date: 2026-09-03 (Asia/Karachi)

## Scope

Run `example-20260902-231103` executed the 180-second `narrow-spike-v1`
workload and its oracle forecast on the disposable three-node
`kind-forecast-error-artifact` cluster. The cluster ran Kubernetes v1.34.0.
The benchmark and controller images were built from the packaged pinned
Dockerfiles and imported into the cluster before execution.

This is a functional artifact test. It is not one of the paper's 142 accepted
runs and is not evidence about the paper's effect estimates.

## Strict evidence audit

- The deterministic request schedule contains 5,550 unique request IDs. The
  request records contain the same IDs and the same scheduled offset, source
  second, target rate, and per-second request count for every ID. Completion
  order differs from schedule order because requests execute concurrently.
- All 5,550 requests returned HTTP 200; there were zero recorded errors and
  zero timeouts. Maximum dispatch lateness was 15.841 ms.
- The oracle file and controller log each contain 180 ordered one-second
  decisions. Decision sequence numbers are exactly 0--179 and tick offsets are
  exactly 0--179,000 ms.
- Every controller forecast value equals the supplied oracle value. Every raw
  replica decision agrees with the pinned capacity lookup.
- All four scaling API updates succeeded. The controller scaled 1 to 4 at
  second 54, then applied the 30-second scale-down stabilization rule and
  scaled 4 to 3, 3 to 2, and 2 to 1 at seconds 113, 114, and 115.
- Kubernetes collection contains 221 contiguous snapshots with no collection
  errors. Median sampling interval was 999.554 ms; P99 was 1,012.714 ms and the
  maximum was 1,013.552 ms.
- Desired replicas first reached four at `t0 + 55.155 s`; four replicas were
  first Ready at `t0 + 56.856 s`, before the workload transition at second 60.
  Desired replicas returned through three, two, and one at approximately
  seconds 113.713, 114.693, and 115.702.
- The normalized causal timeline contains exactly 180 contiguous rows. All 180
  rows contain controller and Kubernetes evidence, and the dispatched-request
  total is 5,550.

The runner completed end-to-end and wrote its success marker without invoking
the recovery finalizer. An earlier retained run, `example-20260902-224234`, had
been misclassified by the first Windows PowerShell wrapper even though its
collector produced complete evidence. The corrected runner classifies success
from validated evidence and was cleanly re-executed in the run audited here.

## Evidence digests

| File | SHA-256 |
|---|---|
| `raw/load-generator-requests.jsonl` | `ca9dd02754accfe7d6b3821716491f6b9d65eea2a5a14a1c5a33b526e2958ec6` |
| `raw/kubernetes-snapshots.jsonl` | `63227c7d57db0ea798c696f0f0cfbb4c17d6110fa619d1d8af374c2d59289fdc` |
| `raw/controller.jsonl` | `849f6274cfb7e6f1952a24473a72e6b8af3bf9056d9ba2780c37876124517ba7` |
| `normalized/joined-timeline.csv` | `441c93610d776780708c944d16010d900ec048fb1700adeedc2b39f0bb8e725f` |

## Interpretation boundary

The load generator reached the benchmark through `kubectl port-forward`.
Request evidence identifies one serving Pod even though Kubernetes observed
four Ready replicas. A port-forward can remain attached to one backend, so the
local latency distribution does not measure four-Pod load balancing or
capacity. The run validates deployment, replay, control decisions, scaling,
readiness, request integrity, collection, and normalization only.
