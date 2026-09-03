# Evidence Ledger 09 - Answers to the Main and Primary Research Questions

## Main research question

**When workload forecasts have similar conventional accuracy, why do they produce different Kubernetes scaling decisions, SLO violations, and resource costs?**

### Direct answer

Forecasts with similar or identical MAE/RMSE produced different outcomes when their errors occupied different operational positions relative to discrete replica thresholds, workload events, and Pod-readiness time. MAE and RMSE aggregate error magnitude across time and remove the sign, event identity, temporal placement, and remaining lead time that determine whether the controller requests too few replicas, requests too many, or requests the correct count too late to become Ready.

The controlled experiments identify three principal pathways:

1. **Decision-boundary pathway:** error direction changes whether predicted demand crosses a replica threshold. Persistent -5 RPS bias selected too few replicas at a 60 RPS sustained peak, while +5 RPS bias selected the oracle count despite identical MAE/RMSE.
2. **Harm-versus-cost pathway:** equal error budgets before versus after an event generate underprovisioning or overprovisioning. Shortened peaks and missed events caused deficiency; extended and false peaks caused excess occupancy.
3. **Readiness-timing pathway:** equal aggregate decision error can occur at operationally different times. Early and late narrow-spike forecasts had identical desired-replica error, but late requests arrived with insufficient readiness lead time and produced multi-second P99 latency.

Forecast structure did not matter when it remained inside the same decision regions. Sharpened and smoothed forecasts produced identical actions and outcomes; periodic early and late forecasts produced identical capacity summaries. Therefore, the mechanism is not structural difference by itself. It is structural difference that changes threshold crossing, under/over direction, or readiness at an important event.

### Evidence strength

- Seven controlled accuracy-matched contrasts, 8 matched pairs each.
- Large raw exact effects for direction, duration, event presence, and narrow-spike timing.
- After Holm adjustment over prespecified domains, most individual primary effects did not cross 0.05.
- The P99 timing-by-workload interaction did survive Holm correction: +2562.12 ms, 95% CI [2226.89, 2953.05], adjusted p = 0.0234375.
- Effects are supported primarily by controlled contrast, magnitude, interval, pair consistency, and robustness—not by isolated p-values.

### Scope

The answer applies to the tested predictive controller, empirical capacity lookup, one-to-four replica range, selected workloads, six-second baseline horizon, and Azure/K3s benchmark environment. It does not establish universal behavior for every autoscaler or application.

## Primary research question

**When MAE and RMSE are held approximately constant, how do forecast-error direction, timing, duration, shape, and transition location affect Kubernetes scaling decisions, capacity readiness, tail-latency SLOs, and resource waste?**

## Direction

### Tested

Persistent -5 RPS versus +5 RPS bias on a sustained-peak workload, with MAE = RMSE = transition MAE = 5 RPS in both conditions.

### Observed magnitude

Positive minus negative bias:

- desired-replica MAE: -0.5861;
- deficient replica-seconds: -211;
- request P99: -12.86 ms, CI [-14.75, -10.79];
- composite-SLO duration: -8.25 s, CI [-13.625, -3.5];
- excess replica-seconds: 0.

### Mechanism and boundary

Negative bias fell below the three-to-four replica boundary at the 60 RPS peak; positive bias matched the oracle decision. Ready-deficit magnitude disappeared under optimistic +10% capacity accounting, so the capacity-harm claim is calibration-dependent. Positive bias did not create resource waste in this pair.

## Duration

### Tested

Shortened versus extended sustained peak, with MAE 2.9661 RPS and RMSE 10.1889 RPS in both conditions.

### Observed magnitude

Shortened minus extended:

- desired-replica MAE: 0 difference (0.25 each);
- deficient replica-seconds: +90;
- request P99: +1543.79 ms, CI [1269.02, 1866.57];
- composite-SLO duration: +6 s, CI [0.25, 11.5], with 5 positive and 3 negative pairs;
- excess replica-seconds: -90.

### Mechanism and boundary

Premature forecast termination scaled down during real demand, while extended termination held capacity after demand declined. Equal absolute decision error became harm versus cost. Transition MAE distinguished the forecasts (0 versus 17.5 RPS), and safety was not tested.

## Event presence

### Tested

Missed versus false narrow spike, with MAE 6.0345 RPS and RMSE 14.5330 RPS in both conditions.

### Observed magnitude

Missed minus false:

- desired-replica MAE: +0.3333;
- deficient replica-seconds: +180;
- request P99: +4805.43 ms, CI [4101.49, 5503.29];
- composite-SLO duration: +49.25 s, CI [43.375, 55.25];
- excess replica-seconds: -120.

### Mechanism and boundary

The missed forecast withheld capacity during a real event; the false forecast supplied unused capacity for a nonexistent event. The direction persisted across all SLO definitions, capacity factors, repetitions, and leave-one-pair-out checks. Transition MAE also distinguished the pair.

## Timing

### Tested

Early versus late shifts under periodic and narrow-spike workloads, with equal MAE/RMSE within each workload.

### Observed magnitude

Periodic late minus early:

- identical desired-replica error, deficiency, and excess capacity;
- P99 +3.40 ms, CI [1.95, 4.91];
- SLO +2.625 s, CI [-1.625, 6.75].

Narrow-spike late minus early:

- identical desired-replica error, deficiency, and excess capacity;
- P99 +2565.51 ms, CI [2233.30, 2954.57];
- SLO +8.625 s, CI [4.5, 13.5].

P99 timing-by-workload interaction:

- +2562.12 ms;
- CI [2226.89, 2953.05];
- Holm-adjusted p = 0.0234375.

### Mechanism and boundary

Late spike prediction left less lead time than Pod readiness required. Periodic timing shifts were operationally diluted and produced the same capacity trajectories. Increasing horizon from 3 to 9 s reduced late-spike SLO duration by 16.2 s and Ready deficit by 216 RPS-s in the prospective robustness campaign.

## Transition location

### Tested

Equal-MAE/RMSE error during a stable versus transition period of a gradual ramp.

### Observed magnitude

Transition minus stable:

- transition MAE: +1.6 RPS;
- desired-replica MAE: +0.0229;
- deficient replica-seconds: 0;
- excess replica-seconds: +11;
- P99: -1.17 ms, CI [-2.98, 0.26];
- SLO duration: -1.625 s, CI [-5.75, 2.0].

### Mechanism and boundary

The altered transition decisions remained on the overprovisioning side, so the effect became small resource cost rather than harm. Transition placement was not inherently harmful.

## Shape

### Tested

Sharpened versus smoothed periodic-triangle forecasts with equal MAE, RMSE, and transition MAE.

### Observed magnitude

- desired-replica MAE, deficiency, and excess: all exactly zero in both conditions;
- P99 difference: -0.42 ms, CI [-2.05, 0.81];
- SLO difference: +0.5 s, CI [-2.5, 3.75].

### Mechanism and boundary

Both shapes remained inside the same replica-decision regions. Visual forecast shape did not matter without a threshold or readiness consequence.

## Safety-net effect across the primary structures

Direct causal safety evidence exists only for persistent negative bias and missed peaks:

- persistent bias: deficiency -96.7%, P99 -32.2%, SLO -34.8% on average, +17 oracle-relative excess replica-seconds;
- missed peak: deficiency -88.3%, P99 -48.1%, SLO -75%, +15 oracle-relative excess replica-seconds.

Safety was not directly tested for duration, timing, location, shape, false peaks, or overprediction. It must be reported as not tested for those structures.

## Reliability of the primary findings

### Strongest controlled practical findings

- missed versus false harm/cost asymmetry;
- shortened versus extended harm/cost exchange;
- persistent negative versus positive decision-boundary effect;
- late narrow-spike harm;
- safety protection for missed peaks and deficiency under persistent bias.

### Multiplicity-qualified findings

Most primary raw p-values were small, but no individual primary mutation outcome crossed 0.05 after Holm adjustment within the prespecified domain families. Decision and cost effects commonly reached 0.0546875. This is not proof of no effect; it reflects seven contrasts across multiple outcome families with eight pairs each.

### Adjusted inferential finding

The narrow-spike-versus-periodic P99 timing interaction survived Holm correction at 0.0234375.

### Negative findings

- shape did not affect controller or operational outcomes;
- periodic timing did not affect capacity summaries and barely affected P99;
- transition placement created only modest excess cost and no harm;
- positive persistent bias did not create oracle-relative excess;
- persistent-bias safety SLO improvement was heterogeneous;
- capacity calibration did not change controller behavior for a fully missed peak;
- transient-versus-persistent was not identified by an accuracy-matched randomized contrast.

## Central hypothesis disposition

The central hypothesis is supported with qualification. Equal aggregate MAE/RMSE can conceal operationally important differences caused by direction, event presence, duration, and readiness-relative timing. However, not every structural difference matters: shape and periodic timing can be operationally equivalent when controller thresholds and readiness trajectories are unchanged. More context-sensitive metrics help, but no single forecast metric uniquely determines reliability and cost.

## Final bounded primary-RQ answer

Within the tested system, error direction, duration, event presence, and timing changed Kubernetes outcomes by changing which replica boundary was crossed, whether decision error represented under- or overprovisioning, and whether requested replicas were Ready at the critical workload event. Shape and transition placement had limited or cost-only effects when they did not create a capacity shortage. Consequently, equal MAE/RMSE does not imply equal autoscaling quality, but structural error differences matter only through the controller and workload mechanisms they activate.
