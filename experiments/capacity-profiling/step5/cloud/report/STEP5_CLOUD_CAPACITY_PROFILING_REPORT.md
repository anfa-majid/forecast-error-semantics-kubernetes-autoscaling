# Step 5 Cloud K3s Capacity Profiling Report

## Executive result

The native three-node Azure K3s campaign established `C_pod = 30 RPS` and the empirical lookup `C_1=30`, `C_2=40`, `C_3=55`, `C_4=65 RPS`.

| Ready Pods | Safe capacity | Ideal N x 30 | Efficiency |
|---:|---:|---:|---:|
| 1 | 30 RPS | 30 RPS | 1.000 |
| 2 | 40 RPS | 60 RPS | 0.667 |
| 3 | 55 RPS | 90 RPS | 0.611 |
| 4 | 65 RPS | 120 RPS | 0.542 |

The oracle/controller must use the lookup table, not `ceil(W/30)`, because scaling efficiency decreases with replica count.

## Frozen SLO and guardrails

P99 latency <= 300 ms; failure rate < 1%; achieved throughput >= 99% of offered load; mean Pod CPU <= 450m; CPU throttled-period ratio < 10%; no readiness loss, restart, or replica change.

## Final formula

`replicas(W) = min { N in {1,2,3,4} : W <= C_N }`, with `C={1:30,2:40,3:55,4:65}`. Loads above 65 RPS are outside the validated four-replica range.

## Key findings

1. The client had to run inside Azure; PC-to-Malaysia measurements contained roughly 240 ms of public-network latency and were rejected as capacity evidence.
2. CPU throttling, not request failure, was the conservative boundary at the selected multi-Pod levels.
3. Kubernetes balanced total requests well, but per-Pod arrivals were bursty enough to create throttling before average CPU reached 450m.
4. Four Pods ran across two workers, so the four-Pod result is replica scaling on two machines, not four-node scaling.
5. The imported image required the digest-qualified alias in K3s containerd's `k8s.io` namespace; this was an implementation detail, not an architectural redesign.
