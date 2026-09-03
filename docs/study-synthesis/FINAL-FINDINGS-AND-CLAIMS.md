# Step 20 - Final Findings and Claims

## 1. Purpose and evidential standard

This document converts the completed experimental and statistical results into defensible answers to the research questions. It distinguishes:

- controlled forecast-mutation evidence;
- controlled safety on/off evidence;
- prospective and offline robustness evidence;
- supplementary ranking associations;
- negative, non-significant, and non-identifiable findings.

Causal language is restricted to matched controlled comparisons. Ranking correlations are not used as causal evidence. Effect magnitude, uncertainty, pair consistency, multiplicity, mechanism, workload context, and system scope are reported together.

## 2. Research questions

### Main research question

When workload forecasts have similar conventional accuracy, why do they produce different Kubernetes scaling decisions, SLO violations, and resource costs?

### Primary research question

When MAE and RMSE are held approximately constant, how do forecast-error direction, timing, duration, shape, and transition location affect Kubernetes scaling decisions, capacity readiness, tail-latency SLOs, and resource waste?

### Secondary research question

How does a fixed reactive safety mechanism change the operational impact of different forecast-error structures?

## 3. Evidence base

- Step 15 primary experiment: seven controlled accuracy-matched A/B contrasts, eight matched repetitions per side, 112 runs.
- Step 16 safety ablation: two errors, five matched safety off/on repetitions each, 20 runs including Step 15 comparators.
- Step 17 analysis population: 142 accepted runs and 59,400 aligned seconds.
- Step 18 inferential analysis: exact paired sign-flip tests, 20,000-resample paired bootstrap intervals, effect sizes, Holm adjustment, interaction analysis, and 14-condition ranking analysis.
- Step 19 offline sensitivity: 200/300/500 ms SLO thresholds, composite versus latency-only definitions, 90/100/110% capacity accounting, and leave-one-pair-out checks.
- Step 19 prospective sensitivity: 40 retained cloud runs covering 3/9 s horizon, 1/3 s safety persistence, and 90/110% controller-capacity settings.

The run is the inferential unit. One-second bins and repeated events are not treated as independent replicates.

## 4. Answer to the main research question

Forecasts with equal MAE and RMSE produced different Kubernetes outcomes because aggregate accuracy removes the information used by the controller and experienced by the system: error sign, event identity, temporal direction, decision-boundary position, and lead time relative to Pod readiness.

Three mechanisms explain the observed differences.

### 4.1 Decision-boundary mechanism

At the sustained 60 RPS peak, the frozen capacity lookup assigned 55 RPS to three replicas and 65 RPS to four. A persistent -5 RPS forecast supported three replicas, while a +5 RPS forecast supported four, despite both having MAE = RMSE = 5 RPS. Negative bias caused 211 deficient replica-seconds; positive bias matched the oracle and produced no oracle-relative excess.

### 4.2 Harm-versus-cost mechanism

Error position relative to the workload event determined whether an incorrect decision removed needed capacity or retained unneeded capacity.

- Shortened peaks caused 90 deficient replica-seconds; extended peaks caused 90 excess replica-seconds.
- Missed peaks caused 180 deficient replica-seconds; false peaks caused 120 excess replica-seconds.

Thus equal aggregate error became service harm under underprediction and resource cost under overprediction.

### 4.3 Readiness-timing mechanism

Early and late narrow-spike forecasts had equal MAE, RMSE, desired-replica MAE, and aggregate deficient/excess replica-seconds. Late forecasting nevertheless added 2565.51 ms request P99 and 8.625 composite-SLO seconds. The late request left insufficient lead time for capacity to become Ready before the short spike.

### 4.4 Boundary of the explanation

Structural difference alone was insufficient. Sharpened and smoothed forecasts remained in the same replica-decision regions and produced identical actions and capacity outcomes. Periodic early/late forecasts also produced identical capacity summaries. Forecast structure mattered when it activated a decision-boundary, under/overprovisioning, or readiness mechanism.

## 5. Answer to the primary research question

### 5.1 Error direction

**Tested:** persistent negative versus positive 5 RPS bias on a sustained peak; eight matched pairs; equal MAE, RMSE, and transition MAE.

**Observed:** positive minus negative bias reduced desired-replica MAE by 0.5861, deficiency by 211 replica-seconds, P99 by 12.86 ms (95% CI -14.75 to -10.79), and SLO duration by 8.25 s (CI -13.625 to -3.5). Excess replica-seconds were zero in both conditions.

**Reliability:** all eight pairs agreed for decision error, deficiency, and P99; raw exact p = 0.0078125. Holm-adjusted p-values were 0.0546875 for decision and 0.1640625 for harm.

**Mechanism:** error sign placed the forecast on opposite sides of the three-to-four replica boundary.

**Workload context:** sustained 60 RPS peak.

**Safety:** persistent-bias safety reduced deficiency from 211 to 7 and P99 by 32.2%, but SLO reduction was heterogeneous.

**Limitation:** Ready-deficit distinction disappeared under optimistic +10% capacity accounting. Positive bias did not create resource waste in this pair.

### 5.2 Error duration

**Tested:** shortened versus extended sustained peak; eight matched pairs; equal MAE and RMSE.

**Observed:** shortened minus extended caused +90 deficient replica-seconds, +1543.79 ms P99 (CI 1269.02 to 1866.57), +6 composite-SLO seconds (CI 0.25 to 11.5), and -90 excess replica-seconds. Desired-replica MAE was identical at 0.25.

**Reliability:** all eight pairs agreed for deficiency, P99, and excess capacity; composite-SLO directions were five positive and three negative. No effect crossed Holm-adjusted 0.05.

**Mechanism:** premature termination removed capacity while demand remained high; extension retained capacity after demand fell.

**Workload context:** sustained peak and falling transition.

**Safety:** not directly tested.

**Limitation:** transition MAE was not matched and successfully distinguished the two forecasts.

### 5.3 Event presence

**Tested:** missed versus false narrow spike; eight matched pairs; equal MAE and RMSE.

**Observed:** missed minus false caused +180 deficient replica-seconds, +4805.43 ms P99 (CI 4101.49 to 5503.29), +49.25 SLO seconds (CI 43.375 to 55.25), and -120 excess replica-seconds.

**Reliability:** every pair agreed; raw exact p = 0.0078125. The direction survived all SLO definitions, capacity factors, and leave-one-pair-out checks.

**Mechanism:** missing real demand prevented predictive scale-out; false demand created unused capacity without a shortage.

**Workload context:** isolated narrow spike.

**Safety:** reduced missed-peak deficiency by 88.3%, P99 by 48.1%, and SLO duration by 75%, while adding capacity.

**Limitation:** transition MAE distinguished the pair; exact magnitudes are specific to the tested spike and replica limit.

### 5.4 Error timing and workload interaction

**Tested:** late versus early forecasts under periodic and narrow-spike workloads; eight matched pairs per workload; equal MAE/RMSE within workload.

**Observed:** periodic lateness changed P99 by only +3.40 ms and did not change decision/capacity summaries. Narrow-spike lateness added 2565.51 ms P99 (CI 2233.30 to 2954.57) and 8.625 SLO seconds (CI 4.5 to 13.5), while aggregate desired-replica error and deficient/excess replica-seconds remained identical.

**Reliability:** P99 timing-by-workload interaction = +2562.12 ms, CI 2226.89 to 2953.05, Holm-adjusted p = 0.0234375. SLO interaction remained uncertain.

**Mechanism:** late spike scale-out occurred with insufficient readiness lead time; periodic structure diluted the timing shift.

**Workload context:** severe for a narrow spike, small for the tested periodic triangle.

**Safety:** no direct early/late safety ablation.

**Robustness:** increasing horizon from 3 to 9 s reduced late-spike SLO duration by 16.2 s and Ready deficit by 216 RPS-s across all five prospective pairs.

**Limitation:** timing cannot be generalized independently of workload shape and horizon.

### 5.5 Stable versus transition placement

**Tested:** equal-MAE/RMSE error during stable versus transition periods of a gradual ramp; eight matched pairs.

**Observed:** transition placement increased desired-replica MAE by 0.0229 and excess capacity by 11 replica-seconds, but caused no deficiency. P99 changed by -1.17 ms (CI -2.98 to 0.26) and SLO duration by -1.625 s (CI -5.75 to 2.0).

**Reliability:** cost and decision differences were deterministic but reached Holm-adjusted 0.0546875; reliability differences were split and uncertain.

**Mechanism:** changed decisions stayed on the overprovisioning side.

**Workload context:** gradual ramp.

**Safety:** not directly tested.

**Limitation:** transition placement is not inherently harmful; direction and boundary crossing determine consequence.

### 5.6 Forecast shape

**Tested:** sharpened versus smoothed periodic-triangle forecast; eight matched pairs; equal MAE, RMSE, and transition MAE.

**Observed:** desired-replica MAE, deficiency, and excess were exactly zero for both. P99 difference was -0.42 ms (CI -2.05 to 0.81); SLO difference was +0.5 s (CI -2.5 to 3.75).

**Reliability:** no reproducible effect; pair directions were mixed and p-values large.

**Mechanism:** both shapes mapped to the same replica decisions.

**Workload context:** periodic triangle.

**Safety:** not directly tested.

**Limitation:** the result demonstrates operational equivalence for this mutation, not that forecast shape can never matter.

## 6. Answer to the secondary research question

The fixed safety rule converted much of underprediction harm into additional requested capacity by raising a replica floor after two observed overload windows.

### 6.1 Missed peak

- Deficient replica-seconds: 180 to 21 (-88.3%).
- P99: 5197.66 to 2697.31 ms (-48.1%; CI -3175.03 to -1825.67).
- SLO duration: 60 to 15 s (-75%; CI -47.405 to -42.2).
- Oracle-relative excess: +15 replica-seconds.
- Total requested-capacity premium: +174 replica-seconds and two additional actions per run.

### 6.2 Persistent negative bias

- Deficient replica-seconds: 211 to 7 (-96.7%).
- P99: 48.72 to 33.03 ms (-32.2%; CI -19.44 to -11.94).
- SLO duration: 26.4 to 17.2 s (-34.8%; CI -18.8 to 3.0).
- Oracle-relative excess: +17 replica-seconds.
- Total requested-capacity premium: +221 replica-seconds and no additional net action transitions per run.

### 6.3 Mechanism and residual harm

Every run intervened once and released once. Missed-peak readiness delay ranged from 1 to 6 s; persistent-bias delay was 1 s. Safety could not protect the two-window detection period or the readiness interval, so it reduced rather than eliminated harm.

### 6.4 Error-specific effect

The missed-peak P99 benefit was 2484.66 ms larger and SLO benefit 35.8 s larger than for persistent bias. The predictive controller provided no event protection for a missed peak, whereas it partially responded to persistent bias.

### 6.5 Robustness and cost trade-off

Increasing trigger persistence from 1 to 3 s added 2.8 SLO seconds, 61 Ready-deficit RPS-s, and 1269.66 ms P99 while saving 5.8 deployment replica-seconds. Faster reaction improved protection at a modest additional capacity cost.

### 6.6 Statistical boundary

With five pairs, the minimum two-sided exact p-value was 0.0625. Safety effects are large and consistently directed for deficiency and P99 but cannot be called conventionally significant under this design. Persistent-bias SLO improvement was heterogeneous, including one worsened repetition.

### 6.7 Bounded secondary-RQ answer

The fixed safety mechanism causally reduced harm for the two tested underprediction errors by converting deficiency into resource occupancy. It was especially effective for missed peaks, but detection and readiness left residual harm and the cost form differed by error. No direct safety conclusion is available for duration, timing, placement, shape, false peaks, or overprediction.

## 7. Conventional metric usefulness

MAE and RMSE were incomplete, not useless.

- MAE versus desired-replica MAE: Spearman 0.786, Kendall 0.686.
- RMSE versus desired-replica MAE: Spearman 0.749, Kendall 0.588.
- Desired-replica MAE versus deficiency: Spearman 0.718, Kendall 0.645.
- RMSE versus P99: moderate Spearman 0.427.

They failed to distinguish causal harm/cost differences within matched direction, duration, event-presence, and spike-timing pairs. They appropriately tied the operationally equivalent shape pair and approximately reflected the equal controller outcomes in periodic timing.

Transition MAE detected several event-local structures but did not map uniquely to harm. It distinguished duration, missed/false, placement, and spike-timing pairs, yet transition placement caused cost without harm.

Forecast and operational rankings were not interchangeable. RMSE versus SLO duration had Spearman -0.573 and 72.9% pairwise disagreement. P99 versus SLO duration had Spearman -0.319 and 61.5% disagreement. These associations are supplementary and dataset-specific.

## 8. Negative, null, and non-identifiable findings

1. Sharpened and smoothed shapes produced identical controller and capacity outcomes.
2. Periodic early/late forecasts produced identical deficiency and excess summaries.
3. Transition placement produced modest excess cost but no reliability harm.
4. Positive persistent bias did not create oracle-relative excess capacity.
5. Shortened-peak composite-SLO effects were heterogeneous despite consistent deficiency/P99 effects.
6. Persistent-bias safety worsened composite harm in one repetition; its SLO interval included zero.
7. Safety did not eliminate harm and always added capacity.
8. The 90% versus 110% prospective controller-capacity contrast did not reliably change missed-peak outcomes because complete event omission dominated the parameter.
9. A randomized accuracy-matched transient-versus-persistent contrast was absent; causal comparison is not identifiable.
10. No global error-by-workload-by-safety mixed model was identifiable because most error types occurred in one workload and safety covered only two errors.
11. Most primary and safety outcomes did not cross 0.05 after prespecified Holm correction.

## 9. Robustness and claim boundaries

### Claims that remain strong

- Missed peaks caused more harm than false peaks, while false peaks caused more resource waste.
- Late narrow-spike forecasts caused greater latency/SLO harm than early forecasts.
- Forecast horizon moderated timing harm.
- The fixed safety rule reduced missed-peak harm and exchanged protection for capacity.
- Aggregate forecast metrics did not substitute for operational outcome metrics.

### Claims requiring qualification

- Persistent-negative-bias Ready deficit depends on capacity calibration.
- Shortened peaks were worse on average, not in every composite-SLO pair.
- Transition error is not inherently harmful.
- Safety benefit magnitude depends on trigger persistence and SLO definition.
- SLO rankings apply to the composite construct; latency-only rankings differ.

### System scope

Evidence is limited to one benchmark application, one three-node Azure/K3s cluster, CPU-oriented workload behavior, horizontal scaling, one-to-four replicas, the empirical capacity lookup, selected workload traces, and the tested predictive/safety controllers. Decision-interval, workload-intensity, second-application, larger-cluster, and alternative autoscaler checks were not completed prospectively.

## 10. Final contribution

The study contributes a controlled framework for translating forecast-error structure into autoscaling consequence. Its central result is not simply that forecast accuracy matters. It is that forecast error must be interpreted through the controller and workload:

`forecast structure -> replica decision -> readiness timing -> service harm or resource cost`

Equal aggregate error can therefore be operationally unequal, while visibly different forecasts can be operationally equivalent when they map to the same decisions. A fixed reactive safety layer can correct much of underprediction harm, but only after detection and readiness, and only by paying a measurable capacity premium.

## 11. Final defensible claims

1. Equal MAE/RMSE does not imply equal autoscaling consequence within the tested system.
2. Error direction matters when it changes a discrete replica boundary.
3. Missing real demand produces greater reliability harm than forecasting false demand, whereas false demand primarily creates resource cost.
4. Premature versus delayed peak termination exchanges capacity deficiency for excess occupancy.
5. Timing harm depends on workload shape and forecast lead time relative to readiness delay.
6. Aggregate desired-replica error can conceal readiness-timing harm.
7. Transition MAE adds useful event-local information but is not a universal operational metric.
8. Forecast-shape differences that do not change controller decisions need not change outcomes.
9. Reactive safety reduces and converts underprediction harm rather than eliminating it.
10. Safety protection and cost depend on the error structure and trigger persistence.
11. Forecast, decision, reliability, and cost rankings answer different questions and should be reported together.

These claims are causal only for the controlled comparisons and system configurations actually tested.
