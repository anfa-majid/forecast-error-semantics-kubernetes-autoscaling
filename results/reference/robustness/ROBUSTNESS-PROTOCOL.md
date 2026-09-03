# Step 19 — Prospective Robustness Protocol

## Status and purpose

This protocol is frozen before inspecting Step 19 sensitivity results. Its purpose is to test whether the principal Step 18 conclusions survive reasonable alternative measurement assumptions and a limited set of prospective system configurations.

## Baseline configuration

- Pod-capacity lookup: 1→30, 2→40, 3→55, 4→65 RPS.
- Composite SLO: latency P99 ≤300 ms, failure rate <1%, completion ratio ≥99% per one-second bin.
- Forecast horizon: 6 seconds.
- Decision interval: 1 second.
- Safety overload persistence: 2 seconds.
- Safety release hold: 30 seconds.
- Workload intensity: frozen Step 15/16 traces.
- Maximum replicas: 4.

## Claims selected before sensitivity analysis

1. Missed peaks cause more operational harm than false peaks while false peaks cause more excess capacity.
2. Shortened peaks exchange the resource premium of extended peaks for operational harm.
3. Late narrow spikes are more harmful than early narrow spikes, and more timing-sensitive than periodic workloads.
4. Persistent negative bias causes greater capacity deficiency than positive bias.
5. The fixed safety rule converts much of missed-peak and persistent-underprediction harm into additional capacity cost.
6. Aggregate forecast accuracy rankings do not substitute for operational rankings.

## Offline sensitivity grid

### SLO definition

Recompute run-level and paired SLO duration using latency thresholds of 200, 300, and 500 ms under:

- latency-only SLO;
- composite SLO retaining the baseline failure and completion rules.

No request or one-second record is discarded. Cross-bin completion effects are retained in the composite definition and removed only in the explicitly labeled latency-only sensitivity.

### Capacity-accounting assumption

Multiply every point in the empirical Ready-capacity lookup by 0.90, 1.00, and 1.10. Recompute:

- Ready-capacity deficit in RPS-seconds;
- Ready-replica deficiency using the scenario lookup.

This is an accounting sensitivity, not a controller counterfactual. Observed controller commands and Ready replica trajectories remain fixed.

### Influence and conclusion stability

For the selected claims, report every matched difference and leave-one-pair-out mean range. A claim is directionally robust when every scenario estimate and every leave-one-pair-out estimate retains the baseline direction. Practical magnitude is reported continuously; it is not converted into a post-hoc binary significance label.

### Ranking stability

Recompute condition-median SLO rankings for every SLO scenario and compare them using Spearman correlation, Kendall tau-b, top-one agreement, and pairwise ordering disagreement. Forecast metrics remain unchanged.

## Prospective cloud checks

Offline reanalysis cannot establish how alternative controller configurations would change commands, readiness, or latency. The minimal prospective campaign will therefore target the highest-risk assumptions:

1. forecast horizon 3 and 9 seconds for the early/late narrow-spike pair;
2. decision interval 2 seconds for missed versus false peak;
3. workload intensity 80% and, only if the capacity ceiling is not structurally binding, 120% for missed versus false peak;
4. safety persistence 1 and 3 seconds for missed peak safety on/off;
5. controller capacity lookup at 90% and 110% of baseline for persistent negative bias or missed peak.

The baseline 6-second, 1-second cadence, 100% intensity, 2-second safety persistence results will be reused only where the raw forecast/workload trace and all other system settings are exactly identical. New configuration cells require new run IDs and immutable evidence.

## Replication count and stopping

Target five matched repetitions per new robustness contrast as a resource-conscious minimum, with the limitation that two-sided exact tests cannot attain p<0.05 at n=5. Runs may be replaced only for frozen technical-invalidity rules, never for unfavorable outcomes. No scenario will be stopped early because a desired direction appears or disappears.

## Interpretation rules

- **Robustly supported:** direction persists across all relevant offline scenarios and prospective configurations, with materially nontrivial magnitude.
- **Configuration-dependent:** direction or practical magnitude changes across plausible settings.
- **Suggestive/underpowered:** direction is consistent but uncertainty or exact-test resolution is inadequate.
- **Exploratory:** comparison was not randomized or fully crossed.
- **Not identifiable:** required factors are confounded or the necessary experiment was not run.

Statistical significance is neither required nor sufficient for robustness. Contradictory findings will be retained.

