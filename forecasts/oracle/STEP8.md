# Step 8 - Oracle Decision Reference

Status: complete oracle policy specification and reference generator  
Version: `1.0.0`

## Executive result

Step 8 implements a deterministic oracle that gives the fixed replica policy perfect knowledge of the true workload six seconds ahead. It generated complete desired-replica timelines for all five Step 7 traces.

The oracle is not an optimal or instantaneous autoscaler. It uses the same limits, empirical capacity mapping, scale-up behavior and scale-down behavior required of every experimental forecast condition. Kubernetes Deployment, Pod Ready and EndpointSlice serving state remain separate runtime observations.

## Authoritative capacity rule

The generic theoretical formula is `ceil(w(t+h)/C_pod)`. It is not used directly because Step 5 measured nonlinear multi-Pod scaling. For this environment:

`raw_replicas(t) = min {N in {1,2,3,4} : true_workload(t+6) <= C_N}`

where `C={1:30, 2:40, 3:55, 4:65}` RPS.

| True workload at t+6 | Raw requirement |
|---:|---:|
| 0-30 RPS | 1 Pod |
| >30-40 RPS | 2 Pods |
| >40-55 RPS | 3 Pods |
| >55-65 RPS | 4 Pods |

Workloads above 65 RPS are rejected because they are outside the validated capacity envelope.

## Frozen policy

| Parameter | Value |
|---|---:|
| Decision interval | 1 second |
| Oracle horizon | 6 seconds |
| Minimum replicas | 1 |
| Maximum replicas | 4 |
| Initial replicas | 1 |
| Additional safety factor | 1.0 |
| Scale-up | Immediate jump to bounded requirement |
| Scale-up cooldown | 0 seconds |
| Scale-down stabilization | Rolling maximum of latest 30 decision samples |
| Maximum scale-down step | 1 Pod per decision |
| Scale-down cooldown | 0 seconds |

The safety factor is 1.0 because the Step 5 capacity values are already conservative safe capacities. Applying another unmeasured margin would double-count conservatism.

## Decision stages

Each timeline preserves:

1. Current true workload.
2. True workload at the six-second target.
3. Safety-adjusted workload.
4. Raw empirical replica requirement.
5. Bounded requirement after min/max limits.
6. Stabilized requirement after the 30-second rolling maximum.
7. Prior and new commanded replicas.
8. Action: `none`, `scale_up` or `scale_down`.
9. Whether scale-down was held by stabilization.

## Manual calculations

- At 25 RPS, the empirical requirement is one Pod.
- At 35 RPS, the empirical requirement is two Pods.
- At 50 RPS, the empirical requirement is three Pods, although `ceil(50/30)` incorrectly gives two.
- At 60 RPS, the empirical requirement is four Pods, although `ceil(60/30)` incorrectly gives two.
- At 65 RPS, the empirical requirement is four Pods.

When the requirement jumps from one to four, the command immediately becomes four. When it falls from four to one, the prior high requirement is retained through the 30-second stabilization window. The controller then commands three, two and one across three decisions because scale-down is limited to one Pod per decision.

## Generated timelines

| Trace | Decisions | Scale-up actions | Scale-down actions | Held scale-down decisions |
|---|---:|---:|---:|---:|
| gradual-ramp-v1 | 480 | 3 | 3 | 87 |
| narrow-spike-v1 | 180 | 1 | 3 | 29 |
| sustained-peak-v1 | 360 | 1 | 3 | 29 |
| periodic-triangle-v1 | 720 | 11 | 11 | 302 |
| stable-noisy-control-v1 | 240 | 0 | 0 | 0 |

The stable/noisy control remains at one desired Pod throughout. Mandatory traces create deterministic scaling decisions suitable for later forecast comparisons.

## Desired versus Ready capacity

Oracle timelines contain desired policy decisions only. They do not fabricate Kubernetes readiness.

- `commanded_replicas`: correct controller request under perfect workload knowledge.
- `deployment_spec_replicas`: accepted desired state observed from Kubernetes.
- `pod_ready_count`: runtime Pod Ready observation.
- `service_ready_count`: runtime EndpointSlice serving-capacity observation.

Decision error compares experimental and oracle commands. Deficient/excess replica-seconds compare observed service-ready capacity with the oracle reference. Even the oracle can experience a readiness deficit if Kubernetes actuation takes longer than the six-second lead.

## Verification

- Nine unit tests cover golden vectors, empirical boundaries, nonlinearity, invalid inputs, immediate scale-up, stabilization and scale-down steps.
- Eight manual capacity cases are replayed independently.
- Every generated decision is independently replayed through a fresh policy engine.
- Every raw Step 8 requirement is checked against the preliminary six-second empirical oracle field produced in Step 7.
- Horizon, sequence, limits, step restrictions and reference semantics are checked.
- Step 7 input hashes are recorded in the oracle manifest.
- The checksum ledger covers immutable package inputs and outputs. The validator's rerunnable summary and generated Python bytecode caches are intentionally excluded because validation rewrites them and they are not research artifacts.
- Golden policy vectors define the acceptance contract for the future Go controller.

## Architecture note

Step 2 selected Go for the production controller. The current environment has no Go compiler and Docker is stopped. The verified Step 8 reference is therefore implemented in Python as the executable scientific oracle and language-neutral policy contract. The future Go controller must pass the included golden vectors and produce identical decisions before forecast experiments begin. This limitation is explicit; no uncompiled implementation is presented as tested.

## Completion checklist

| Step 8 requirement | Evidence | Status |
|---|---|---|
| Oracle calculation implemented | `tools/policy.py` and `tools/generate_oracle.py` | Complete |
| True workload at selected horizon | `true_future_workload_rps`, target offsets and 6000-ms horizon | Complete |
| Same min/max and capacity assumptions | Frozen policy configuration and golden vectors | Complete |
| Same stabilization and step constraints | Stateful policy engine and tests | Complete |
| Oracle timelines for every workload | Five files in `timelines/` | Complete |
| Deterministic results | Unit tests, replay validation and input hashes | Complete |
| Manual checks | `samples/manual-calculations.csv` | Complete |
| Oracle plots | Five files in `plots/` | Complete |
| Desired and Ready references separated | `readiness-reference-contract.json` | Complete |
| Future controller equivalence contract | `samples/golden-policy-vectors.json` | Complete |

Step 8 is complete as an oracle reference. Before the experimental controller is accepted, its Go decision engine must pass the same golden vectors and equality tests.
