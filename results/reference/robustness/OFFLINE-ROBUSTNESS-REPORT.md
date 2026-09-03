# Step 19 — Offline Robustness Results

## Scope

This report covers sensitivity checks that can be performed without changing the observed controller or cluster trajectory. It uses all 59,400 aligned seconds and all 142 accepted runs. Prospective controller, horizon, cadence, workload-intensity, and safety-threshold experiments remain separate.

## SLO-definition sensitivity

Run-level SLO duration was recomputed at latency thresholds of 200, 300, and 500 ms under both latency-only and composite definitions. The composite definition retained failure-rate ≥1% and completion-ratio <99% components.

### Missed versus false peak

The missed-peak effect remained positive in all six scenarios and every leave-one-pair-out analysis. The mean additional SLO duration ranged from 32.75 seconds under latency-only 500 ms to 49.25 seconds under the composite definition. Every repetition favored the same direction in all scenarios.

Conclusion: the claim that missed peaks are more harmful than false peaks is robust to plausible latency thresholds and to removal of the failure/completion components.

### Late versus early narrow spike

The late-spike effect remained positive in all six scenarios, ranging from 7.875 to 8.75 additional SLO seconds. Every repetition retained the same direction, and every leave-one-pair-out estimate remained positive.

Conclusion: the timing-direction result for narrow spikes is robust to the tested SLO definitions.

### Shortened versus extended peak

The shortened-peak effect remained positive across all scenarios, ranging from 5.875 to 9.375 additional SLO seconds. Under the composite definition, five pairs were positive and three negative; under latency-only definitions all eight were positive. Leave-one-pair-out mean effects remained positive.

Conclusion: the mean direction is robust, but pair-level heterogeneity depends on whether completion/failure components are included. The claim should emphasize average operational harm rather than universal run-level dominance.

### Safety for missed peaks

Safety reduced SLO duration in all six scenarios and every repetition. The mean reduction ranged from 25.4 seconds under latency-only SLOs to 45 seconds under composite SLOs. Every leave-one-pair-out estimate retained a benefit.

Conclusion: the missed-peak safety benefit is not an artifact of the 300 ms latency threshold. Its numerical magnitude partly reflects the composite completion/failure definition.

## Capacity-accounting sensitivity

The empirical Ready-capacity lookup was multiplied by 0.90, 1.00, and 1.10 while keeping observed Ready replicas and controller commands unchanged. This tests the capacity construct, not counterfactual controller behavior.

### Missed versus false peak

The missed peak produced more Ready-capacity deficit under every lookup: 1,200.75, 1,183.125, and 1,120.5 RPS-seconds at factors 0.90, 1.00, and 1.10. Every pair and every leave-one-pair-out estimate retained the direction.

Conclusion: the capacity-harm asymmetry between missed and false peaks is robust to ±10% capacity calibration.

### Safety for missed peaks

Safety reduced Ready-capacity deficit by 1,107.1, 1,101.0, and 1,055.8 RPS-seconds across the three capacity assumptions. Every repetition and leave-one-pair-out estimate retained the benefit.

Conclusion: the safety capacity benefit is robust to the tested capacity accounting range.

### Persistent positive versus negative bias

The positive-minus-negative bias contrast changed from −1,620 RPS-seconds at 90% capacity to −900 at baseline and exactly zero at 110%. The apparent Ready-capacity deficiency of negative bias therefore depends on the calibrated capacity boundary. At +10%, three Ready replicas are treated as sufficient for the sustained 60 RPS peak.

Conclusion: the broad statement that persistent negative bias necessarily creates Ready-capacity deficit is configuration-dependent. The defensible claim is narrower: under the baseline and conservative capacity calibrations, negative bias created more measured deficit; this distinction vanished under the optimistic calibration. The latency and decision-error findings remain separate and are not invalidated by this accounting result.

## Ranking sensitivity

Composite-SLO condition rankings were almost invariant across 200–500 ms: Spearman correlation with baseline was 1.000 at 200 ms and 0.9989 at 500 ms, with unchanged top-ranked condition and no discordant comparable pair orderings.

Latency-only rankings were very different: Spearman correlation with the baseline composite ranking was −0.125, Kendall tau-b −0.070, top-one agreement was absent, and 55.6% of comparable condition pairs were ordered differently. Many ties reduced the comparable-pair count.

Conclusion: rankings are robust to the numerical latency threshold within the composite construct, but not to changing the construct from composite SLO harm to latency-only harm. Final claims must name the SLO construct explicitly.

## Claims after offline sensitivity

### Remain strong

- Missed peaks create more harm than false peaks.
- Late narrow spikes are more harmful than early narrow spikes.
- Safety materially reduces missed-peak harm while adding capacity cost.
- Aggregate accuracy rankings do not substitute for operational rankings.

### Require qualification

- Shortened peaks are worse on average, but composite-SLO pair-level outcomes are heterogeneous.
- Safety effect magnitude depends on whether completion and failure are included in the SLO.
- SLO rankings apply to the composite operational construct and should not be generalized to latency-only rankings.
- Persistent-negative-bias Ready-capacity deficiency depends on capacity calibration and disappears at the optimistic +10% lookup.

## What this analysis cannot establish

Changing the forecast horizon, decision interval, workload intensity, controller capacity lookup, or safety persistence changes controller actions and potentially the Ready trajectory. Existing logs cannot establish those counterfactual operational outcomes. Those assumptions require prospective cloud runs or must remain explicit external/configuration-validity limitations.

