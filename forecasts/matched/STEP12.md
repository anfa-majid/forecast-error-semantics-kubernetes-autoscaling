# Step 12 - Accuracy-Matched Forecast Dataset

Status: protocol, grid search, matching, semantic validation, visual review, independent validation, and dataset freeze complete  
Version: `1.0.0`  
Protocol: `anfa-accuracy-matching-protocol-v1`  
Candidates: 96  
Accepted primary pairs: 7

## Executive result

Step 12 fixes the central independent-variable dataset for the final experiments. It creates forecast pairs derived from the same actual workload that have equal conventional accuracy but different temporal or semantic error structure.

The deterministic outcome-blind search evaluated 96 candidates and 428 eligible-side comparisons. Seven primary pairs were accepted, covering direction, duration, event presence, location, shape, periodic timing, and spike timing. Every accepted pair has exactly equal MAE and RMSE: relative difference is 0% for both metrics, comfortably within the frozen 2% MAE and 3% RMSE tolerances.

No Kubernetes latency, failure, readiness, utilization, or replica outcome was used to rank or select pairs. The candidate metric table supplied to the selector contains forecast and semantic fields only. Forecast-driven policy timelines were generated only after selection and are marked descriptive.

Seven unit tests and sixteen independent validation checks pass. A clean rebuild reproduces 239 generated artifacts byte-for-byte.

## Purpose and hypothesis role

Conventional forecast metrics collapse temporal structure:

```text
MAE  = mean(|forecast - oracle|)
RMSE = sqrt(mean((forecast - oracle)^2))
```

Two forecasts can have the same MAE and RMSE while one error occurs before a peak and another after it, one removes real demand while another invents demand, or one affects a stable period while another affects a scaling transition. Step 12 isolates these semantic differences while controlling aggregate error magnitude.

Each pair uses:

- the same Step 7 actual workload;
- the same trace duration and request schedule;
- the same six-second forecast horizon;
- the same Step 8/9 capacity and stabilization policy;
- the same Step 9 forecast CSV contract; and
- distinct preregistered semantic sides.

Cross-workload matching is prohibited because it would confound forecast semantics with workload shape.

## Preregistered matching protocol

The frozen rules are stored in `configuration/matching-protocol.json`.

### Accuracy tolerances

For metric values `a` and `b`, symmetric relative difference is:

```text
D(a,b) = 2*|a-b| / (|a|+|b|)
```

Acceptance requires:

```text
D(MAE_A,MAE_B)  <= 0.02
D(RMSE_A,RMSE_B) <= 0.03
```

Candidates must also have MAE and RMSE of at least 0.20 RPS, preventing trivial near-zero matches and unstable relative comparisons.

### Matching loss

Eligible pairs are ranked by:

```text
L = D(MAE_A,MAE_B)/0.02 + D(RMSE_A,RMSE_B)/0.03
```

All accepted pairs have `L=0`.

### Deterministic tie-breaking

When several pairs have equal loss, selection uses:

1. lower preregistered parameter-preference distance;
2. lower parameter complexity; and
3. lexicographic candidate IDs.

Preferred severities were fixed for interpretability: 10-second spike timing, 15-second periodic phase, 5-RPS persistent bias, 30-second duration, 30-second/35-RPS event presence, 60-second/8-RPS location, and 10-second shape radius.

### Candidate reuse

The 14 forecasts in the seven primary pairs are unique. Eligible alternatives remain in the distance table, but a candidate cannot appear in two primary pairs.

## Outcome-blinding controls

The selector is forbidden from reading:

- commanded or Ready replicas;
- replica disagreement, excess, or deficiency;
- request latency, status, timeout, or failure;
- CPU, memory, throttling, or network metrics; and
- Kubernetes events.

`metrics/candidate-metrics.csv`, the actual selector input, contains none of these fields. Selection uses only identity, forecast-error metrics, parameters, affected support, and semantic measurements.

The algorithm creates `post-selection-policy-reference.csv` only after a pair has been selected and frozen. These timelines support later feasibility review and plotting but cannot influence matching.

## Parameter grids

| Contrast | Workload | Grid |
|---|---|---|
| Spike timing | narrow-spike-v1 | early/late shifts 5, 10, 15, 20 s |
| Periodic timing | periodic-triangle-v1 | early/late shifts 5, 10, 15, 20, 30 s |
| Direction | sustained-peak-v1 | persistent +/-2, 3, 4, 5 RPS |
| Duration | sustained-peak-v1 | shortened/extended 10, 20, 30, 45, 60 s |
| Event presence | narrow-spike-v1 | missed true peak; false durations 20/30/40 s and levels 50/55/60 RPS |
| Location | gradual-ramp-v1 | stable/transition errors of 20/30/45/60 s and 4/6/8/10 RPS |
| Shape | periodic-triangle-v1 | smoothing and residual-mirrored sharpening radii 2,3,4,5,6,8,9,10,12 s |

This produces 96 valid candidates within 0-65 RPS.

## Transparent protocol amendment

The initial shape grid contained radii 2-8 seconds. All had MAE below the already-frozen 0.20-RPS minimum, so the matcher correctly found no eligible shape pair. Before any Kubernetes outcome was examined, radii 9, 10, and 12 were added and the preferred shape radius changed to 10.

The accuracy tolerances, minimum-error gates, semantic rules, same-workload rule, and outcome blinding were unchanged. The complete amendment is recorded in `validation/protocol-amendment-log.json`.

## Semantic acceptance gates

| Group | Required distinction |
|---|---|
| Spike/periodic timing | opposite timing signs and at least 10 s absolute displacement |
| Direction | opposite signed bias and at least 3 RPS absolute bias |
| Duration | opposite duration-error signs and at least 20 s absolute error |
| Event presence | missed versus false event and support Jaccard <=0.10 |
| Location | stable versus transition phase and zero support overlap |
| Shape | smoothed versus sharpened, radius at least 2 s |

Pairs need not differ on every semantic metric. An early/late pair can correctly share zero signed bias and equal duration; its preregistered contrast is timing.

## Accepted matched pairs

| Pair | Workload | Forecast A | Forecast B | MAE | RMSE | MAE diff | RMSE diff |
|---|---|---|---|---:|---:|---:|---:|
| pair-01-direction_bias | sustained peak | persistent -5 RPS | persistent +5 RPS | 5.000000 | 5.000000 | 0% | 0% |
| pair-02-duration | sustained peak | extended 30 s | shortened 30 s | 2.916667 | 10.103630 | 0% | 0% |
| pair-03-event_presence | narrow spike | false 60-RPS peak for 30 s | missed true peak | 5.833333 | 14.288690 | 0% | 0% |
| pair-04-location | gradual ramp | +8 RPS stable error for 60 s | +8 RPS transition error for 60 s | 1.000000 | 2.828427 | 0% | 0% |
| pair-05-shape | periodic triangle | sharpened radius 10 s | smoothed radius 10 s | 0.297068 | 0.723647 | 0% | 0% |
| pair-06-timing_periodic | periodic triangle | 15 s early | 15 s late | 6.475000 | 7.331097 | 0% | 0% |
| pair-07-timing_spike | narrow spike | 10 s early | 10 s late | 3.888889 | 11.666667 | 0% | 0% |

## Semantic evidence

### Direction

The two persistent forecasts change every decision by exactly -5 or +5 RPS. Signed biases are -5 and +5 RPS while MAE/RMSE remain exactly 5 RPS.

### Duration

One forecast retains the sustained peak 30 seconds too long; the other ends it 30 seconds too early. Duration errors are +30 and -30 seconds with equal residual magnitude.

### Event presence

The false forecast inserts a 60-RPS, 30-second peak in a stable interval. The missed forecast removes the real 60-RPS, 30-second peak. Their supports do not overlap (`Jaccard=0`); residual blocks are equal magnitude with opposite signs.

### Location

Both forecasts add 8 RPS for exactly 60 seconds. One interval is in the final stable period beginning at target second 420; the other begins at the upward transition at second 60. Supports do not overlap.

### Shape

The smoothed forecast applies a centered 10-second moving average around repeated periodic extrema. The sharpened forecast is defined as:

```text
sharpened = 2*oracle - smoothed
```

Their residuals are exact sign mirrors, guaranteeing identical absolute and squared error while creating visibly opposite shape effects. Values remain within validated capacity.

### Timing

Periodic events shift -15 versus +15 seconds. The narrow spike shifts -10 versus +10 seconds. In both pairs, translation symmetry yields identical MAE/RMSE and opposite peak timing.

## Search and rejection accounting

- Candidates generated: 96
- Cross-side comparisons evaluated: 428
- Accepted primary pairs: 7
- Explicitly rejected comparisons: 395
- Other eligible comparisons: retained as nonselected alternatives in the full distance table

Rejection reasons include MAE tolerance, RMSE tolerance, minimum error, insufficient timing/duration/bias separation, and excessive affected-support overlap. Every rejected row contains machine-readable reasons in `rejected-pairs/rejection-ledger.csv`.

## Forecast and directory contracts

Each accepted directory contains:

```text
accepted-pairs/<pair-id>/
  forecast-a.csv
  forecast-b.csv
  pair-metadata.json
  post-selection-policy-reference.csv
```

Forecast CSVs use the exact Step 9 columns, consecutive one-second issue offsets, constant 6,000-ms horizon, stable mutation IDs, and values within 0-65 RPS. Accepted files are byte-identical copies of their candidate files.

Supporting outputs include candidate metadata, candidate metrics, full pair-distance table, rejection ledger, PNG/SVG plots, matched dataset manifest, and validation results.

## Pair plots

Every pair plot shows:

1. oracle workload and Forecasts A/B;
2. residuals for A/B;
3. post-selection oracle and forecast-driven replica references; and
4. labeled Step 7 workload phases.

Plots state that the replica panel was created only after matching was frozen. Visual review confirms event-presence, location, shape, and timing distinctions.

## Test and validation evidence

Seven unit tests verify symmetric relative difference, timing sign gates, direction gates, duration gates, location overlap rejection, shape sides/radius, and operational-field prohibition.

Sixteen independent dataset checks verify:

- protocol status and hash;
- seven distinct groups;
- same-workload pairs;
- accuracy tolerances;
- semantic gates;
- no candidate reuse;
- outcome-blind provenance;
- absence of operational selector fields;
- accepted/candidate byte equality;
- Step 9 forecast contract;
- independent MAE/RMSE recomputation;
- complete search ledger and rejection reasons;
- plot coverage; and
- byte-exact regeneration of 239 artifacts.

Final validation result: `valid: true`.

## Limitations and interpretation

- Exact matching is a feature of symmetric deterministic constructions, not evidence that the forecasts are realistic learned-model outputs.
- The seven primary pairs are a controlled methodological dataset. A later experiment-matrix step may limit which pairs receive repeated cluster runs, but it must not redefine them after observing outcomes.
- Pairwise matching controls MAE/RMSE within each workload, not across workloads.
- Shape-pair MAE is deliberately smaller than other groups but remains above the preregistered minimum.
- Forecast-driven replica references are descriptive only and are not live Kubernetes results.
- Statistical replication, run randomization, blocking, exclusion criteria, and inferential analysis belong to later steps.

## Completion assessment

| Written Step 12 requirement | Evidence | Status |
|---|---|---|
| Similar MAE and RMSE | all seven pairs have exact equality | Complete |
| Predetermined tolerances | frozen 2%/3% protocol | Complete |
| Parameter/candidate search | 96-candidate deterministic grid | Complete |
| Different temporal semantics | seven preregistered contrast groups | Complete |
| Timing distinction | early/late spike and periodic pairs | Complete |
| Direction distinction | persistent negative/positive pair | Complete |
| Duration distinction | shortened/extended pair | Complete |
| Shape distinction | sharpened/smoothed pair | Complete |
| Affected-region distinction | stable/transition and false/missed pairs | Complete |
| Signed bias checked | candidate and pair metadata | Complete |
| Peak timing/amplitude/duration checked | independently derived metrics | Complete |
| No operational cherry-picking | forbidden-field controls and outcome-blind provenance | Complete |
| Rejection criteria | protocol plus 395-row rejection ledger | Complete |
| Accepted pairs and metric table | matched manifest and distance table | Complete |
| Validation plots | seven PNG/SVG pair plots and review record | Complete |
| Forecast contract | independent accepted-file validation | Complete |
| Reproducibility | byte-exact clean rebuild and hashes | Complete |

## Final conclusion

Step 12 is complete. The central forecast-treatment dataset is fixed before live operational experiments: seven same-workload pairs are exactly matched on MAE and RMSE, remain strongly distinct in preregistered semantic structure, and were selected without Kubernetes outcome information.
