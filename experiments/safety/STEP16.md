# Step 16 - Reactive Safety-Net Ablation

## Frozen causal question

For persistent underprediction and a missed narrow peak, how much SLO and ready-capacity harm is prevented or corrected by one fixed reactive rule, and what extra capacity or scaling activity does that protection require?

## Fixed algorithm

The authoritative observation is the load generator's actual dispatch count in each completed one-second window. It is reactive offered demand, not forecast demand, future schedule data, successful throughput, CPU, or latency.

1. Read the last completed demand window and current Ready replicas.
2. Use `C={1:30,2:40,3:55,4:65}` RPS to estimate Ready capacity.
3. Mark overload when observed demand exceeds Ready capacity.
4. Require two consecutive overload windows.
5. Raise a safety floor to the current-demand replica requirement.
6. Arbitrate `final command = max(predictive command, safety floor)` in one controller.
7. Keep the floor while observed demand still requires more replicas than the predictive command; after that protection need clears for 30 consecutive seconds, release it.
8. Delegate scale-down to the unchanged predictive policy.

The detection delay and Kubernetes actuation delay are intentional residual-harm intervals.

## Frozen treatments

- Persistent negative bias on `sustained-peak-v1`: five safety-on repetitions.
- Missed peak on `narrow-spike-v1`: five safety-on repetitions.
- Safety-off comparison: corresponding accepted Step 15 repetitions with identical workloads and forecasts.

Late-event and false-peak tests remain possible later extensions; they are not silently added to the preregistered matrix.

## Required evaluation

Log one safety decision per second. Measure first overload/intervention, intervention count and duration, predictive/safety/final/Ready replicas, command-to-Ready delay, deficient Ready replica-seconds, SLO harm before detection/during actuation/after readiness, avoided and residual harm, extra replica-seconds, and extra scaling actions.

## Validity boundaries

Parameters are identical across conditions; the predictive forecast and policy stay unchanged; one controller owns scale writes; missing observations never use carry-forward or fabricated zero; >65 RPS invalidates the run; only technical invalidity permits a same-cell rerun.

## Observation transport contract

The safety-enabled load generator counts dispatches at the moment each request is actually submitted, before waiting for its response. It finalizes each one-second window 150 ms after the window boundary and posts one strict JSON observation to the controller. This avoids confusing delayed completions or timeouts with reduced offered demand. The controller accepts only the configured run ID, exact sequential windows, and rates that equal dispatch count divided by window duration. Duplicate, missing, reordered, cross-run, malformed, or out-of-envelope data invalidates the run rather than invoking fallback behavior.
