# Step 11 - Controlled Forecast Mutation Framework

Status: design, implementation, generation, testing, visual review, and independent validation complete  
Version: `1.0.0`  
Generator: `anfa-forecast-mutation-generator-v1`  
Candidate forecasts: 23 across five workloads

## Executive result

Step 11 implements a reusable deterministic framework that begins with the true six-second-ahead workload forecast and introduces one controlled forecast-error semantic at a time. It generates timing, event-presence, direction/bias, duration, shape, and location errors while preserving the actual workload, request schedule, forecast horizon, controller policy, and experimental environment.

The framework produced 23 candidate forecasts covering every required mutation semantic. Each candidate includes a Step 9-compatible forecast CSV, complete JSON metadata and parameters, affected target-time and issue-time intervals, forecast error metrics, forecast-driven replica timeline, operational replica-error metrics, PNG/SVG plots, and cryptographic hashes.

Seven unit tests and fifteen independent catalog validations pass. The validator independently regenerates 122 artifacts byte-for-byte, verifies that no mutation changes values outside its declared support, verifies every forecast's timing/range contract, and confirms exact oracle-policy equality with all five Step 8 authoritative timelines.

## Purpose and causal role

The framework is not a forecasting model and does not learn from data. It is an experimental treatment generator. For a decision issued at time `t`, the oracle input is:

```text
f_oracle(t) = actual_workload(t + 6 seconds)
```

A mutation operator `M(theta, interval)` produces:

```text
f_mutated(t) = M(f_oracle, theta, interval)
```

Only the forecast is changed. The following remain frozen:

- Step 7 workload values and exact request schedules;
- one-second decision interval;
- six-second forecast horizon;
- Step 8 empirical capacity policy;
- Step 9 controller implementation and stabilization;
- Step 10 telemetry and run validation.

This isolation allows later operational differences to be attributed to forecast-error semantics rather than controller retuning or workload variation.

## Target-time versus issue-time contract

All mutation semantics are defined in **forecast target time**, because an error such as “late peak by 10 seconds” describes the predicted future event. Forecast CSVs are indexed by controller issue time.

For horizon `h=6`:

```text
target_second = issue_second + 6
issue_second  = target_second - 6
```

Metadata saves both affected target-time and derived issue-time intervals. This prevents an accidental six-second displacement when replaying a mutation through the controller.

Targets beyond the workload end use the final stable workload value, exactly matching the Step 7/8 terminal-extension rule.

## Frozen capacity and controller policy

| Forecast RPS | Raw requirement |
|---:|---:|
| 0-30 | 1 Pod |
| >30-40 | 2 Pods |
| >40-55 | 3 Pods |
| >55-65 | 4 Pods |

The generator applies the same policy as Steps 8 and 9:

- minimum 1 and maximum 4 replicas;
- safety factor 1.0;
- immediate scale-up;
- maximum bounded requirement over the latest 30 decisions for scale-down stabilization;
- maximum scale-down step of one Pod per decision;
- values above 65 RPS rejected.

The generic `ceil(RPS/30)` formula is not used because Step 5 established nonlinear multi-Pod capacity.

## Mathematical mutation definitions

Let `f(t)` be the oracle forecast, `g(t)` the mutated forecast, `I` the declared target-time support, `b` a baseline, `a` an additive bias, `alpha` an amplitude factor, and `clip` the validated `[0,65]` range. The generator rejects a parameterization that would require unrecorded clipping.

### Additive bias

```text
g(t) = f(t) + a,  t in I
g(t) = f(t),      t outside I
```

Negative `a` creates underprediction; positive `a` creates overprediction. A full-trace interval creates persistent bias. A short interval creates transient bias. An annotation-selected stable or transition interval creates location-controlled error.

### Amplitude or slope scaling

```text
g(t) = b + alpha * (f(t) - b), t in I
```

`alpha<1` reduces amplitude/slope; `alpha>1` exaggerates it. The baseline-relative definition avoids scaling the baseline itself.

### Event shift

For an event occupying `[s,e]` and shift `delta`:

```text
g(t) = f(t-delta), when t-delta is inside [s,e]
g(t) = baseline,   in the vacated/added support otherwise
g(t) = f(t),       outside union([s,e],[s+delta,e+delta])
```

Negative `delta` is early; positive `delta` is late. This relocates the event and explicitly clears its original-only portion.

### Global periodic phase shift

```text
g(t) = f(t-delta)
```

Boundary values use deterministic endpoint extension. It is used for repeated early/late periodic errors.

### Missed and false peaks

Missed peak:

```text
g(t) = local_baseline, t in true peak interval
```

False peak:

```text
g(t) = specified false-event amplitude, t in annotated stable interval
```

The primary true event is otherwise unchanged.

### Shortened and extended peaks

Shortened peak replaces the final `d` seconds of the true event with baseline. Extended peak replaces the next `d` seconds after the true event with peak amplitude. The declared support is exactly the removed or added segment.

### Moving-average smoothing

For radius `r`:

```text
g(t) = mean(f(t-r), ..., f(t+r))
```

The support expands by `r` seconds around the annotated event. Endpoint extension is deterministic. Values outside the expanded support remain identical.

## Candidate catalog

| Workload | Candidate mutations | Scientific role |
|---|---:|---|
| gradual-ramp-v1 | 5 | early/late trend, slope errors, transition underprediction |
| narrow-spike-v1 | 6 | early/late, missed/false, smoothing, exaggeration |
| sustained-peak-v1 | 7 | under/overprediction, persistent bias, transient error, shortened/extended duration |
| periodic-triangle-v1 | 3 | repeated early/late phase and repeated smoothing |
| stable-noisy-control-v1 | 2 | stable-period error and false peak |
| **Total** | **23** | all required families |

Family totals are six timing, three event-presence, four direction/bias, three duration, five shape, and two location candidates.

The catalog is intentionally broader than the eventual experiment matrix. A later design step can select a smaller, balanced set without changing mutation definitions.

## Mutation metadata contract

Every metadata JSON records:

- mutation and generator versions;
- mutation ID, family, type, and semantic label;
- source workload and suite version;
- complete parameter object;
- six-second horizon and policy identity;
- affected and actually changed target-time intervals;
- affected and actually changed issue-time intervals;
- global and region error metrics;
- Step 7 workload and annotation hashes;
- generated forecast and replica-timeline hashes;
- frozen policy hash; and
- explicit `outside_support_unchanged` result.

The distinction between affected support and actually changed samples is important for smoothing and shifts: a declared support can include boundary samples whose numerical value coincidentally remains equal.

## Forecast CSV contract

Every generated forecast contains exactly:

| Column | Meaning |
|---|---|
| `trace_id` | source Step 7 trace |
| `condition` | semantic forecast condition |
| `issued_offset_ms` | controller decision time |
| `target_offset_ms` | predicted future time |
| `horizon_ms` | fixed 6000 ms |
| `predicted_rps` | deterministic mutated forecast |
| `mutation_id` | exact treatment identity |
| `pair_manifest_id` | candidate-catalog pairing identity |

Offsets start at zero, increase in exact one-second steps, contain no gaps or duplicates, and always satisfy `target-issued=6000 ms`. Values are finite and constrained to 0-65 RPS.

## Forecast error metrics

For residual `r(t)=g(t)-f(t)` over `N` decisions:

```text
MAE  = mean(|r(t)|)
RMSE = sqrt(mean(r(t)^2))
Bias = mean(r(t))
```

Every candidate also records:

- maximum absolute error;
- MAE within declared support;
- changed-decision count;
- peak timing error;
- peak amplitude error;
- affected-region peak residual;
- duration-above-threshold error;
- event-presence classification.

Peak timing uses the first maximum in the discrete trace. It is `null` for a completely missed peak because the predicted event does not exist. For false peaks, the original primary event metrics can remain unchanged while `event_presence_error=false_peak` and affected-region residual identify the inserted event.

Duration uses the midpoint between the oracle trace's minimum and maximum as the event threshold. Periodic candidates therefore measure total above-threshold time across all cycles.

## Operational replica metrics

Both oracle and mutated forecasts pass through the frozen policy. The generated replica timeline saves raw and commanded replicas for each decision. Metrics include:

- replica-disagreement seconds;
- excess replica-seconds;
- deficient replica-seconds;
- false scale-out seconds; and
- missed scale-out seconds.

This separates numerical forecast error from operational effect. Equal MAE does not imply equal capacity behavior.

## Key candidate results

Examples from the generated metric table:

| Candidate | MAE | Timing/duration effect | Replica effect |
|---|---:|---|---:|
| narrow spike early 10 s | 3.889 RPS | peak timing -10 s | 22 disagreement seconds |
| narrow spike late 10 s | 3.889 RPS | peak timing +10 s | 22 disagreement seconds |
| missed spike | 5.833 RPS | event absent, duration -30 s | 180 deficient replica-seconds |
| false stable peak 45 RPS | 1.650 RPS | inserted event | 99 excess replica-seconds |
| sustained underprediction 0.80 | 3.500 RPS | amplitude -7 RPS | 211 deficient replica-seconds |
| shortened sustained peak 30 s | 2.917 RPS | duration -30 s | 90 deficient replica-seconds |
| extended sustained peak 30 s | 2.917 RPS | duration +30 s | 90 excess replica-seconds |
| periodic early/late 15 s | 6.475 RPS | repeated phase +/-15 s | 330 disagreement seconds each |

The complete table is `metrics/mutation-metrics.csv`.

## Visual validation

Every candidate has PNG and SVG plots containing three aligned panels:

1. oracle/actual future workload and mutated forecast;
2. residual `forecast-oracle`; and
3. oracle and forecast-driven commanded replicas.

The declared mutation support is shaded. Representative inspection passed for:

- late narrow spike;
- missed narrow spike;
- extended sustained peak;
- smoothed periodic peaks; and
- false peak in stable/noisy workload.

Automated checks cover every candidate: plot presence, declared support, outside-support equality, residual, and replica outputs. Results are saved in `validation/visual-review.json`.

## Validation and testing

### Unit tests

Seven tests verify:

- every empirical capacity boundary and over-capacity rejection;
- 30-second stabilization and one-Pod scale-down steps;
- oracle terminal extension;
- exact support isolation for bias;
- early/late shift direction;
- interval compaction; and
- unique catalog identities and complete family coverage.

### Independent catalog validation

Fifteen checks verify:

- every required semantic is represented;
- IDs are unique and all five workloads are represented;
- metric and metadata rows are complete;
- parameters and intervals are saved;
- no outside-support mutation occurs;
- Step 9 CSV columns, offsets, horizons, and ranges are exact;
- metadata hashes match artifacts;
- oracle policy output exactly matches all Step 8 timelines;
- all 23 plots exist; and
- 122 generated artifacts reproduce byte-for-byte in a clean temporary directory.

Final validation result: `valid: true`.

## Edge cases and interpretation

### Errors with no commanded-replica effect

Five candidates currently have numerical error but zero commanded-replica disagreement:

- exaggerated narrow spike;
- sustained overprediction;
- persistent positive bias;
- short transient negative bias; and
- smoothed periodic workload.

These are not generator failures. They expose policy mediation:

- a peak already requiring the four-Pod maximum cannot scale higher;
- values can change without crossing an empirical boundary;
- a short underprediction can be suppressed by 30-second scale-down stabilization; and
- smoothing can alter peak shape without changing capacity bands.

They are useful controls but should not replace operationally active candidates if experiment time is limited.

### Flat and repeated maxima

Sustained peaks and periodic traces can contain multiple equal maxima. The generic metric uses the first discrete maximum, while event-presence metadata and annotated supports preserve the intended semantic. A completely missed event has undefined (`null`) timing rather than a misleading baseline timestamp.

### Terminal horizon

The last six decisions target beyond the workload file. They use the final stable value. Mutation support outside the available issued-target range is intersected with actual forecast targets and recorded explicitly.

### Range and clipping

Candidates are parameterized to remain within 65 RPS. The generator rejects rather than silently clips out-of-range values, preventing an undocumented second mutation.

### Parameter severity

This is a candidate catalog, not an accuracy-matched final design. MAE ranges differ by semantic and workload duration. If later hypotheses require equal MAE/RMSE pairs, selection or parameter solving must be performed explicitly and saved as a new catalog version.

## Directory structure

```text
step-11-forecast-mutations-v1.0.0/
  README.md
  STEP11.md
  configuration/
  schemas/
  base-forecasts/
  forecasts/<trace>/
  metadata/<trace>/
  replica-timelines/<trace>/
  metrics/
  plots/<trace>/
  manifests/
  validation/
  tools/
  tests/
```

## Reproduction

From the package root:

```powershell
python tools/generate_mutations.py `
  --step7-root "..\..\workloads" `
  --policy "..\oracle\policy-config.json" `
  --catalog configuration\mutation-catalog.json `
  --output .

python -m unittest discover -s tests -v

python tools/validate_mutations.py `
  --root . `
  --step7-root "..\..\workloads" `
  --step8-root "..\oracle" `
  --policy "..\oracle\policy-config.json" `
  --catalog configuration\mutation-catalog.json
```

No random seed is required because the transformations are deterministic. Input and output hashes prove exact provenance.

## Completion assessment

| Written Step 11 requirement | Evidence | Status |
|---|---|---|
| Begin with oracle forecast | five saved base forecasts and terminal extension | Complete |
| Early and late shifts | ramp, spike, and periodic candidates | Complete |
| Missed and false peaks | narrow/stable candidates | Complete |
| Underprediction and overprediction | sustained candidates | Complete |
| Persistent negative/positive bias | full-trace sustained candidates | Complete |
| Transient/short error | 20-second sustained negative bias | Complete |
| Shortened and extended peak | symmetric 30-second duration candidates | Complete |
| Smoothed and exaggerated peak | spike/periodic smoothing and spike exaggeration | Complete |
| Slope reduction/exaggeration | gradual-ramp candidates | Complete |
| Stable-period and transition-period errors | stable control and gradual transition candidates | Complete |
| Source workload saved | trace identity and input hash | Complete |
| Family/type/parameters saved | catalog and per-candidate metadata | Complete |
| Affected interval saved | target and issue support/change intervals | Complete |
| MAE, RMSE, bias | global and region metric table | Complete |
| Peak timing/amplitude/duration errors | per-candidate metrics and presence convention | Complete |
| Actual/forecast/residual plots | 23 PNG and 23 SVG plot sets | Complete |
| Event regions | shaded declared support | Complete |
| Oracle and forecast replicas | 23 replay timelines and plot panels | Complete |
| Determinism | clean byte-exact regeneration | Complete |
| No unintended outside mutation | all-candidate validator | Complete |
| Edge cases identified | cap, boundary, stabilization, repeated peaks, terminal horizon | Complete |
| Reusable generator and candidate catalog | versioned code/config/artifacts | Complete |

## Final conclusion

Step 11 is complete. The project now has a deterministic, auditable forecast-treatment generator that covers all requested error semantics, records exact parameters and metrics, replays the unchanged autoscaling policy, creates visual evidence, and proves byte-for-byte reproducibility without unintended changes outside target regions.
