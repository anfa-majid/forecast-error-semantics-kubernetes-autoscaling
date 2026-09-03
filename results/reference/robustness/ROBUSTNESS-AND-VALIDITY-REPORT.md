# Step 19 — Robustness and Threats-to-Validity Report

## Executive conclusion

Step 19 is complete for the frozen offline sensitivity grid and the retained 40-run prospective campaign. The results strengthen three conclusions: missed-peak harm is robust to the SLO definition and capacity accounting; late spikes remain worse than early spikes; and a faster reactive trigger protects more effectively than a slower one. They also require two important qualifications: operational rankings depend strongly on whether the SLO is composite or latency-only, and capacity-deficit claims for persistent negative bias depend on the Pod-capacity calibration.

The prospective evidence should be interpreted through effect magnitudes and paired uncertainty, not a binary significance rule. Each contrast has only five matched repetitions; the smallest attainable two-sided exact paired-permutation p-value is 0.0625.

## Evidence base and design

- Offline reanalysis: 142 accepted Step 17 runs and 59,400 aligned seconds.
- Prospective campaign: 40 retained valid runs, four paired contrasts, five repetitions per cell.
- Forecast horizon: 3 s versus 9 s, separately for early and late narrow spikes.
- Safety persistence: 1 s versus 3 s for missed peaks with safety enabled.
- Controller capacity: 90% versus 110% capacity lookup for missed peaks with safety disabled.
- Pairing unit: repetition number within an otherwise matched configuration contrast.
- Uncertainty: deterministic 10,000-sample paired bootstrap percentile intervals.
- Test: exact two-sided paired permutation test over all sign assignments.
- Directional stability: all five pair differences checked explicitly.

Technical failures were replaced only under frozen validity rules. The attempt audit contains 62 attempts: 40 retained, 9 valid but superseded by the controller-v1.1.2 replacement campaign, and 13 technically invalid. No run was excluded because its outcome was unfavorable.

## Prospective results

### Forecast horizon

Changing the horizon from 3 s to 9 s reduced harm in every matched repetition.

- Early spikes: mean composite-SLO duration fell from 16.2 s to 8.4 s (difference −7.8 s; paired bootstrap 95% CI −10.2 to −4.8; exact p=0.0625).
- Late spikes: mean composite-SLO duration fell from 29.0 s to 12.8 s (−16.2 s; CI −21.8 to −10.6; p=0.0625).
- Late-spike Ready-capacity deficit fell from 291 to 75 RPS-s (−216 RPS-s; CI −242 to −179; p=0.0625).
- Late-spike request P99 fell by approximately 1,081 ms on average (CI −1,535 to −545 ms; p=0.0625).

Interpretation: timing errors remain operationally important, but their realized harm is strongly moderated by the forecast horizon relative to readiness delay. The benefit is larger for late forecasts because additional horizon directly reduces the period in which demand arrives before capacity.

### Safety persistence

The 1 s trigger was consistently more protective than the 3 s trigger.

- Composite-SLO duration increased from 13.0 s at 1 s persistence to 15.8 s at 3 s persistence (+2.8 s; CI +1.2 to +4.2).
- Ready-capacity deficit increased from 82 to 143 RPS-s (+61 RPS-s; CI +43 to +82).
- Request P99 increased by approximately 1,270 ms (CI +703 to +1,873 ms).
- The slower trigger used 5.8 fewer deployment replica-seconds on average (CI −6.0 to −5.4), exposing the expected protection–cost trade-off.

Interpretation: the Step 16 safety conclusion is robust, but safety is not a free correction. Faster intervention reduces residual harm at a small additional capacity premium. The trigger threshold must therefore be reported as part of the treatment definition.

### Controller capacity lookup

The 90% versus 110% controller-capacity contrast did not change the controller trajectory in this missed-peak condition: both configurations remained at the minimum until reactive intervention was unavailable. Mean composite-SLO duration was 51.6 versus 58.2 s, but the paired difference was heterogeneous (+6.6 s; CI −3.4 to +16.8; exact p=0.3125). Ready-capacity-deficit differences were also small and inconsistent (+6 RPS-s; CI −12 to +24).

Interpretation: this prospective contrast does not establish that optimistic capacity calibration causes more harm. In this particular missed-peak trace, forecast absence dominated the capacity parameter, so the parameter had little leverage over decisions. This is a genuine negative result and is retained.

## Offline robustness results

- Missed versus false peak retained the same harm direction across 200, 300, and 500 ms thresholds under latency-only and composite SLO definitions. Mean additional SLO duration ranged from 32.75 to 49.25 s.
- Late versus early narrow spike retained the same direction in all SLO scenarios, with 7.875–8.75 additional SLO seconds.
- Shortened versus extended peak retained a positive mean difference, but composite-SLO pair-level effects were heterogeneous.
- Safety reduced missed-peak SLO harm and Ready-capacity deficit in every tested offline scenario.
- Composite-SLO rankings were stable to the numerical latency threshold, but changing to a latency-only construct produced Spearman −0.125, Kendall tau-b −0.070, and 55.6% pairwise ranking disagreement.
- Persistent-negative-bias deficit was present under conservative and baseline capacity accounting but vanished at the optimistic +10% lookup.

## Claim-level disposition

1. **Missed peaks are more harmful than false peaks:** robustly supported within the tested application, workload family, and composite-SLO construct.
2. **False peaks primarily convert error into capacity cost:** supported by the baseline analysis and offline sensitivity.
3. **Late narrow spikes are worse than early spikes:** robustly supported, with magnitude moderated by forecast horizon.
4. **Shortened peaks are worse than extended peaks:** supported on average, not as universal pair-level dominance.
5. **Persistent negative bias necessarily creates deficiency:** narrowed; the measured deficit depends on capacity calibration.
6. **Safety converts harm into cost:** robustly supported for missed peaks; a faster trigger improves protection at a modest replica-second premium.
7. **Forecast accuracy ranking substitutes for operational ranking:** rejected; ranking agreement remains construct-dependent and supplementary.

## Threats to validity

### Internal validity

- Cluster noise and cloud contention remain possible despite matched repetitions and resets.
- Kubernetes telemetry coverage reached a minimum of 94.4% in retained runs. Runs passed the frozen completeness validator, but missing snapshots can blur one-second readiness transitions.
- The controller was amended from v1.1.1 to v1.1.2 to retry transient Ready-replica reads. Earlier safety runs were superseded rather than pooled, preventing a controller-version confound in the retained safety comparison.
- Service endpoint publication and diagnostic logging amendments were operational reliability changes. They are documented and do not vary between retained contrast cells.
- Clock preflight/postflight records and immutable inputs reduce, but do not eliminate, alignment error.

### Construct validity

- Request rate represents demand but does not span memory-, I/O-, or dependency-bound applications.
- The composite SLO combines latency, failures, and completion. Conclusions must name this construct because latency-only rankings differ substantially.
- Replica-seconds are an infrastructure proxy, not monetary or energy cost.
- The empirical capacity lookup is uncertain; this materially affects deficiency conclusions near a capacity boundary.
- P99 from a finite short window is tail-sensitive and should be read alongside duration and failures.

### External validity

- Evidence comes from one benchmark application, one three-node K3s cluster, one cloud environment, horizontal replica scaling, and a maximum of four replicas.
- Only selected narrow-spike and missed-peak cases received prospective robustness runs.
- Decision-interval, workload-intensity, second-application, larger-cluster, and alternative scaling-policy checks were not completed prospectively. Claims cannot be generalized to those settings.

### Conclusion validity

- Five pairs provide useful effect-direction evidence but low inferential resolution.
- Bootstrap intervals with n=5 describe uncertainty in these pairs and should not be treated as broad population guarantees.
- Multiple metrics are correlated; p-values are descriptive and no claim rests on isolated significance.
- Negative and contradictory results are retained, including the capacity-controller contrast.
- The attempt audit guards against outcome-dependent replacement, but technical instability increases execution-history complexity.

## Final bounded conclusion

The strongest defensible result is not that every forecast error with the same MAE has the same consequence. Error timing, event omission, persistence, controller horizon, and reactive trigger latency determine whether error becomes SLO harm, residual capacity deficiency, or resource cost. This conclusion survives the tested SLO thresholds, capacity accounting, forecast horizons, and safety persistence settings. It remains bounded to the application, cluster, workload classes, and horizontal-scaling design studied here.

