# Step 16 — Reactive Safety-Net Ablation

## 1. Completion statement

Step 16 is complete. A deterministic reactive safety-net controller was implemented, commissioned, independently replay-validated, and evaluated in ten paired safety-on/safety-off experiments. All ten planned safety-on cells have one accepted attempt, all accepted attempts use the same frozen protocol and controller image, and every accepted safety decision agrees exactly with an independent reference replay.

The final output is the **Safety-Net Ablation Dataset**, containing one row for each paired repetition and separating SLO harm, residual harm, readiness delay, replica cost, and scaling-action cost.

## 2. Research objective

The objective was to determine which forecast errors can be corrected reactively and what that protection costs. The experiment asks:

1. Does a fixed reactive safety rule reduce SLO harm relative to the same forecast with safety disabled?
2. How much harm occurs before the safety mechanism can intervene?
3. How much harm remains after intervention?
4. How long does requested capacity take to become Ready?
5. How many additional replica-seconds and scaling actions are introduced?
6. Does the answer differ between a short missed peak and persistent negative forecast bias?

## 3. Scope

The frozen Step 14 secondary-safety scope contained ten cells:

- Five repetitions of **persistent negative bias** on `sustained-peak-v1`.
- Five repetitions of **missed peak** on `narrow-spike-v1`.

Each safety-on run was paired with its accepted Step 15 safety-off comparator. The workload schedule and forecast trace within each pair were identical and verified by SHA-256. Step 16 therefore evaluates the two error types frozen for the secondary-safety phase; it does not claim experimental coverage of every forecast-error family discussed in the broader research plan.

## 4. Fixed safety algorithm

### 4.1 Signal

The authoritative signal is the number of requests actually dispatched by the load generator in each completed one-second window. A 150 ms grace interval allows the window to finalize before it is posted to the safety controller.

### 4.2 Capacity model

Ready capacity is estimated from the frozen empirical lookup:

| Ready replicas | Estimated capacity (RPS) |
|---:|---:|
| 1 | 30 |
| 2 | 40 |
| 3 | 55 |
| 4 | 65 |

Demand above 65 RPS is outside the validated controller range and invalidates the run.

### 4.3 Trigger and persistence

An overload window occurs when observed dispatched demand exceeds the estimated capacity of the Deployment's Ready replicas. Safety triggers after two consecutive overload windows. No condition-specific threshold or timing parameter is permitted.

### 4.4 Intervention

When triggered, the safety floor is raised to the minimum replica count capable of serving the current observed demand according to the capacity lookup. The final requested replica count is:

`max(predictive command, safety floor)`

The safety controller never lowers the predictive controller's command. Both predictive and safety decisions pass through a single arbiter and a single Kubernetes scale writer.

### 4.5 Release

The floor remains active while observed demand requires more replicas than the predictive command. Once that protection need clears, the floor is released after a fixed 30-second hold. Scale-down then remains governed by the unchanged predictive policy.

### 4.6 Missing observations

A missing observation is logged and does not trigger an inferred intervention. The controller does not guess demand.

### 4.7 Pseudocode

```text
for each finalized one-second observation:
    ready_capacity = capacity(Deployment.ready_replicas)
    required = minimum replicas for observed dispatched RPS
    overload = observed RPS > ready_capacity

    if overload:
        consecutive_overload_windows += 1
    else:
        consecutive_overload_windows = 0

    if consecutive_overload_windows >= 2:
        safety_floor = max(current safety floor, required)
        safety_active = true
        release_hold = 30 seconds
    else if safety_active:
        if required > predictive_command:
            release_hold = 30 seconds
        else:
            decrement release_hold
        if release_hold == 0:
            safety_active = false
            safety_floor = minimum replicas

    final_command = max(predictive_command, safety_floor)
    log observation, state, event, floor, final command, and API result
```

## 5. Implementation

Controller v1.1.1 adds four safety-specific components:

- A strict observation endpoint accepting sequential, run-matched one-second dispatch windows.
- A deterministic safety state machine implementing persistence and release.
- A thread-safe arbiter computing the maximum of predictive demand and the safety floor.
- Extended decision logging for observed demand, Ready capacity, trigger state, intervention events, floor, final command, readiness, and Kubernetes API results.

The load generator records each dispatch immediately before the request is sent, finalizes every window, writes the observation to local JSONL evidence, and publishes the same record to the controller. Any publishing failure invalidates the attempt.

The commissioned controller artifact was:

- Version: `1.1.1`
- OCI manifest: `sha256:764cfd9be60fd92ce637e6217be950dbd171ee987c469fe5c1e60d6c0807c8a9`
- Exported archive SHA-256: `b4e83aebadf12e77fa7092854c893b17a088c364877cf959898d5733ccd9a843`

The manifest was attested on all three Azure nodes before accepted collection.

## 6. Experimental controls

The following remained fixed:

- Kubernetes: `v1.36.1+k3s1`, three amd64 Ubuntu 24.04.4 nodes.
- Benchmark application image: `anfa/benchmark-app@sha256:0fd880c5401b443a3dfb329c48fe3bd8c844643007a6097f6c31917a47961cee`.
- Predictive policy SHA-256: `86f4add7a80b9288abc82d42e3a1b55ad670b4da9a6a942ba302674ab513193b`.
- Forecast horizon: 6 seconds.
- Decision and observation intervals: 1 second.
- Predictive scale-down stabilization: 30 seconds.
- Replica bounds: 1–4.
- SLO: P99 latency no more than 300 ms, failure rate below 1%, completion ratio at least 99%.
- One active run at a time, frozen execution order, and a 30-second inter-run stable period.

Collection was outcome-blind: high latency, failures, slow readiness, underprovisioning, overprovisioning, and unfavorable outcomes were never grounds for exclusion.

## 7. Validation and evidence integrity

Every accepted run passed all predefined checks:

- Required raw, normalized, metadata, and validation files present.
- Exact matrix, run, workload, forecast, and policy identity.
- One observation, one predictive decision, and one safety decision per workload second.
- Sequential observation and decision identifiers with no gaps or duplicates.
- Exact agreement between observation dispatch counts and request-log dispatch counts.
- Exact safety-policy hash.
- Exact independent replay of all safety decisions and final arbitration results.
- No controller Kubernetes API errors.
- Passed clock attestations.
- A 58-entry checksum manifest.

The completed campaign contains 10 valid cells, 0 pending cells, and no active attempt.

## 8. Metric definitions

An **SLO-harm second** is a one-second normalized timeline row in which at least one of the following holds:

- P99 latency exceeds 300 ms;
- failed/offered requests is at least 1%; or
- completed/offered requests is below 99%.

Because more than one component can fail in one second, component violation counts are not added to form total harm; total harm counts the union of violating seconds.

Other definitions:

- **Intervention time:** safety sequence of the first `intervention_started` event.
- **Readiness delay:** seconds from first intervention until Ready replicas reach the requested final replica count.
- **SLO harm before intervention:** safety-on harm seconds earlier than the first intervention.
- **Residual harm:** safety-on harm seconds at or after intervention.
- **Avoided harm:** safety-off harm seconds minus safety-on harm seconds.
- **Requested replica-second:** one second of a controller-requested replica. Safety-on uses the final arbitrated command.
- **Scaling action:** a change between adjacent one-second requested-replica commands.
- **Additional resource cost:** safety-on requested replica-seconds minus safety-off requested replica-seconds.

These are controller-requested replica-seconds, not cloud billing units and not Ready-replica-seconds.

## 9. Per-run results

| Seq. | Condition | Rep. | First intervention (s) | Ready delay (s) | Harm off | Harm on | Avoided | Classification | Added replica-s | Added actions |
|---:|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 1 | Persistent negative bias | 1 | 61 | 1 | 48 | 29 | 19 | Reduced | 221 | 0 |
| 2 | Missed peak | 1 | 61 | 2 | 66 | 19 | 47 | Reduced | 174 | 2 |
| 3 | Persistent negative bias | 2 | 61 | 1 | 16 | 12 | 4 | Reduced | 221 | 0 |
| 4 | Missed peak | 2 | 61 | 6 | 58 | 18 | 40 | Reduced | 174 | 2 |
| 5 | Persistent negative bias | 3 | 61 | 1 | 13 | 26 | -13 | Increased | 221 | 0 |
| 6 | Missed peak | 3 | 61 | 4 | 60 | 11 | 49 | Reduced | 174 | 2 |
| 7 | Persistent negative bias | 4 | 61 | 1 | 23 | 7 | 16 | Reduced | 221 | 0 |
| 8 | Missed peak | 4 | 61 | 4 | 58 | 14 | 44 | Reduced | 174 | 2 |
| 9 | Persistent negative bias | 5 | 61 | 1 | 32 | 12 | 20 | Reduced | 221 | 0 |
| 10 | Missed peak | 5 | 61 | 1 | 58 | 13 | 45 | Reduced | 174 | 2 |

Every run produced one intervention, requested at most four replicas, and later produced one clean release. No intervention required a second floor-raise event.

## 10. Aggregate results

| Condition | Runs | Harm off | Harm on | Avoided harm | Reduction | Added replica-s | Added actions | Mean Ready delay |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Missed peak | 5 | 300 | 75 | 225 | 75.0% | 870 | 10 | 3.4 s |
| Persistent negative bias | 5 | 132 | 86 | 46 | 34.8% | 1,105 | 0 | 1.0 s |
| Combined | 10 | 432 | 161 | 271 | 62.7% | 1,975 | 10 | 2.2 s |

Across all ten pairs, the safety mechanism reduced measured harm by 271 seconds while adding 1,975 requested replica-seconds and 10 scaling actions.

## 11. Findings by error type

### 11.1 Missed peak / narrow spike

Safety reduced harm in all five repetitions. Harm fell from 300 to 75 seconds, a 75% aggregate reduction. Latency, failure, and completion components all improved. The safety-off predictive controller remained at one replica because the peak was absent from the forecast; safety introduced two command changes per run, corresponding to reactive scale-up and release.

Readiness delay varied from one to six seconds. This delay explains why the safety mechanism reduced rather than eliminated harm: two trigger windows must complete before intervention, and requested pods then require time to become Ready. Each run retained 10–15 post-intervention harm seconds.

The protection premium was consistent: 174 additional requested replica-seconds and two additional scaling actions per repetition.

### 11.2 Persistent negative bias

Aggregate harm fell from 132 to 86 seconds, a 34.8% reduction. Four repetitions improved, while one increased from 13 to 26 harm seconds. All measured harm in these runs came from the per-second completion criterion; neither safety-on nor safety-off produced P99-latency or failure-rate violation seconds.

The safety floor changed the requested command for 208 seconds per run and added 221 requested replica-seconds. It did not add net command transitions because the predictive trajectory already contained the same number of scale changes; safety changed their timing and level rather than their count.

The unfavorable third repetition must be retained. It demonstrates that deterministic reactive protection does not guarantee a better observed outcome in every repetition, particularly when baseline harm is small and completion timing varies across one-second bins. The paired aggregate still indicates reduction, but the mechanism converts sustained forecast bias into a substantial, long-lived capacity premium.

## 12. Interpretation

The fixed rule is most effective for a missed peak. In that case the predictive controller provides no protection, observed overload is unambiguous, and the reactive floor supplies capacity throughout the event. The remaining harm is concentrated in detection and readiness delay.

Persistent underprediction is different. The predictive controller already reacts partially through its forecast path, while the safety floor stays active for much longer. The safety mechanism therefore provides a smaller aggregate harm reduction at a larger replica-second cost. It converts some service harm into sustained overprovisioning, and repetition-level variability remains visible.

The experiments support the following conclusions:

- The safety rule **reduces but does not eliminate** missed-peak harm.
- It **partially reduces** persistent-underprediction harm in aggregate.
- Detection persistence and pod readiness create unavoidable residual harm.
- Protection has a measurable resource premium.
- The premium's form depends on the error: extra actions for missed peaks, sustained replica occupancy for persistent bias.
- A safety net should be reported as a separate controller layer, not treated as evidence that forecast errors are harmless.

## 13. Invalid-attempt audit

The first matrix cell required six attempts. Five were invalid for technical reasons and were preserved:

1. Controller rollout failure before T0.
2. Controller image pull failure, diagnosed from preserved pod evidence.
3. Missing RBAC permission for reading Deployment Ready replicas, causing observation publication failure.
4. Validation exposed omitted false/zero log fields and a safety-policy byte-hash mismatch.
5. PowerShell corrupted an inline ConfigMap immutability patch before deployment.

The accepted sixth attempt used controller v1.1.1 and the final frozen protocol. Attempts 1, 2, and 5 stopped before workload execution; attempts 3 and 4 were rejected by predefined technical validity and replay requirements. None was excluded because of its SLO outcome. After commissioning stabilized, the remaining nine cells passed on their first attempt.

## 14. Limitations and threats to validity

- Experimental scope contains only two frozen forecast-error conditions. Late-event and false-peak behavior are not directly tested in this Step 16 dataset.
- The capacity lookup is empirical and specific to this application, workload generator, cluster, and resource configuration.
- SLO harm is evaluated in one-second bins. Request completions crossing a bin boundary can affect the completion-ratio component even when aggregate request accounting is sound.
- Replica-seconds represent requested capacity, not actual Ready capacity or monetary cloud cost.
- The five repetitions quantify observed run-to-run variability but are not a large sample for broad statistical generalization.
- The safety trigger uses load-generator dispatches, an experimentally authoritative signal that may not be available with identical timing in a production system.
- The controller is bounded at four replicas and 65 RPS; conclusions should not be extrapolated beyond that validated range.
- Safety-on and safety-off runs are paired by input but executed at different times, so transient infrastructure variation cannot be eliminated completely.

## 15. Reproducibility record

Primary artifacts in `step-16`:

- `configuration/safety-policy.json` — frozen rule.
- `configuration/execution-protocol.json` — frozen system and validity contract.
- `matrix/safety-execution-matrix.csv` — ten ordered safety-on cells and Step 15 comparators.
- `state/campaign-state.json` — attempt and acceptance history.
- `results/<run-id>/attempt-<n>/` — immutable raw and normalized evidence.
- `safety-net-ablation-dataset.csv` — analysis-ready paired dataset.
- `safety-net-ablation-dataset.json` — dataset, definitions, and condition summaries.

Accepted evidence uses protocol input hash `e580c32ecf148f07cfd0ecbd34f37038e567df1c52eedf85261ce6fcdbff706d`. Each accepted run contains a local checksum manifest and validation report.

## 16. Completion criteria assessment

| Criterion | Result |
|---|---|
| Safety logic deterministic and fixed | Met |
| Same safety mechanism across conditions | Met |
| Interventions fully logged | Met |
| Same forecasts compared safety-on/off | Met |
| Independent safety replay | Met for every decision |
| Protection separated from resource premium | Met |
| Harm before and after intervention measured | Met |
| Residual and avoided harm measured | Met |
| Additional replica-seconds measured | Met |
| Additional scaling actions measured | Met |
| Safety does not silently alter predictive controller | Met through single-writer arbitration and counterfactual predictive logging |
| Safety-Net Ablation Dataset produced | Met |

## 17. Final conclusion

Step 16 demonstrates that a simple, fixed reactive safety layer can materially reduce forecast-error harm without modifying the forecast or predictive policy. It is particularly effective for missed peaks, where it reduced measured SLO-harm seconds by 75% across all repetitions. Persistent negative bias was harder: aggregate harm fell by 34.8%, but one repetition worsened and the controller paid a larger sustained capacity premium.

The safety net therefore **reduces and converts harm rather than universally eliminating it**. Missed-peak harm is largely converted into short reactive scaling and additional replica occupancy; persistent underprediction is converted into a longer-lived resource cost with residual variability. This is the intended Step 16 completion result.
