# Step 20 - Detailed End-to-End Research Report

## Document status

- Step: 20 - Synthesize the final findings
- Deliverable: Final Findings and Claims Document
- Evidence status: completed and validated
- Analysis scope: synthesis of sealed Steps 15-19 evidence; no new experimental treatment or metric definition
- Validation: 27 traceability checks passed with zero failures before this detailed compilation

## Executive orientation

This report is the self-contained end-to-end record of Step 20. It explains how the completed experimental evidence was converted into answers to the research questions and final bounded claims. The concise integrated findings appear first. The complete contrast-level evidence ledger follows as an appendix so that effect estimates, confidence intervals, tests, mechanisms, workload contexts, safety coverage, negative findings, and prohibited overclaims can be audited without consulting the conversation history.

The report does not replace the sealed raw or analysis-ready data. Quantitative authority remains with the validated Step 17 datasets, Step 18 statistical tables, Step 19 robustness outputs, and the immutable run evidence. Step 20 adds interpretation and traceability only.

## End-to-end research chain

1. Controlled workload traces established known demand events.
2. Forecast mutations changed direction, duration, event presence, placement, shape, or timing.
3. Selected pairs held conventional MAE/RMSE approximately or exactly equal.
4. The predictive controller translated forecasts into desired replicas using a frozen empirical policy.
5. Kubernetes readiness determined when requested capacity could serve traffic.
6. Request-level and one-second telemetry measured latency, failures, completion, utilization, and capacity state.
7. Step 17 aligned the raw evidence and defined reproducible run/event metrics.
8. Step 18 estimated paired effects, uncertainty, interactions, multiplicity-adjusted tests, and ranking agreement.
9. Step 19 tested SLO, capacity, horizon, trigger, and influence sensitivity and bounded validity.
10. Step 20 traced every final claim to those results and separated causal, associational, negative, and non-identifiable evidence.

## Evidence hierarchy

### Tier 1 - Controlled forecast mutations

Seven matched A/B contrasts with eight repetitions per side support causal statements about the changed forecast property within the tested system. The run is the inferential unit.

### Tier 2 - Controlled safety ablation

Identical workload/forecast inputs replayed safety off and on for missed peaks and persistent negative bias support causal statements about the fixed reactive rule. Each error has five matched pairs.

### Tier 3 - Robustness evidence

Offline reanalysis changes measurement assumptions while preserving observed trajectories. Prospective Step 19 runs change selected controller configurations and therefore test operational sensitivity directly.

### Tier 4 - Supplementary association

Condition-level rank correlations summarize agreement among metrics. They are not causal evidence and contain only 14 condition medians with ties.

## Statistical interpretation rules

- Report individual paired direction, absolute/percentage effect, bootstrap interval, exact p-value, and Holm-adjusted p-value together.
- Do not treat p >= 0.05 as proof of no effect.
- Do not call five-pair safety or robustness effects conventionally significant: their minimum two-sided exact p-value is 0.0625.
- Do not promote seconds or repeated events to independent replicates.
- Use causal language only for controlled contrasts.
- Retain negative, null, contradictory, and non-identifiable results.
- Keep P99 magnitude, SLO duration, deficient capacity, and excess capacity as distinct constructs.

## Report map

- Part I: integrated findings, research-question answers, limitations, and final claims.
- Part II: complete evidence ledger for every forecast dimension, safety, metrics, and RQ synthesis.
- Part III: claim traceability, reproducibility, and completion record.

---

# Part I - Integrated Final Findings and Claims


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


---

# Part II - Detailed Evidence Ledger


---

## Appendix 1 - 01 Error Direction

### Evidence Ledger 01 - Forecast-Error Direction

#### Controlled contrast

- Contrast: persistent positive bias minus persistent negative bias.
- Workload: `sustained-peak-v1`.
- Inferential unit: matched run repetition.
- Sample: 8 matched pairs (16 Step 15 runs).
- Forecast control: MAE = 5 RPS, RMSE = 5 RPS, and transition MAE = 5 RPS for both conditions in every repetition.
- Estimand: B minus A, where A is persistent negative bias and B is persistent positive bias.

#### Evidence

| Outcome | Negative bias (A) | Positive bias (B) | Paired effect B-A | 95% paired bootstrap CI | Raw exact p | Holm p | Pair direction |
|---|---:|---:|---:|---:|---:|---:|---|
| Desired-replica MAE | 0.5861 | 0 | -0.5861 (-100%) | [-0.5861, -0.5861] | 0.0078125 | 0.0546875 | 8 negative |
| Deficient replica-seconds | 211 | 0 | -211 (-100%) | [-211, -211] | 0.0078125 | 0.1640625 | 8 negative |
| Request P99 latency | 48.59 ms | 35.73 ms | -12.86 ms (-26.46%) | [-14.75, -10.79] | 0.0078125 | 0.1640625 | 8 negative |
| Composite-SLO duration | 24.875 s | 16.625 s | -8.25 s (-33.17%) | [-13.625, -3.5] | 0.03125 | 0.34375 | 6 negative, 2 ties |
| Excess replica-seconds | 0 | 0 | 0 | [0, 0] | 1 | 1 | 8 ties |

#### Causal interpretation

Because the two forecasts have exactly equal MAE, RMSE, and transition MAE and were replayed as a controlled matched mutation, the direction change caused different controller decisions within this experimental system. At the sustained 60 RPS peak, the baseline capacity lookup treats three Ready replicas as 55 RPS and four as 65 RPS. The -5 RPS forecast lands at 55 RPS and therefore supports a three-replica decision, whereas the +5 RPS forecast lands at 65 RPS and supports four replicas. The negative error is harmful because it falls on the lower side of a discrete replica boundary.

#### Safety evidence

For the persistent-negative-bias condition, safety on versus off (5 matched pairs) changed:

- deficient replica-seconds: 211 to 7, a reduction of 204 (-96.7%);
- request P99: reduction of 15.69 ms (-32.2%), 95% CI [-19.44, -11.94];
- mean SLO duration: reduction of 9.2 s, 95% CI [-18.8, 3.0];
- excess replica-seconds: increase of 17.

All five pairs agreed on deficient-capacity reduction, P99 reduction, and added excess capacity. With five pairs, the minimum possible two-sided exact p-value is 0.0625; the result is a large, consistent practical effect with limited test resolution, not a conventional p<0.05 finding.

#### Robustness qualification

Offline Ready-capacity accounting at 90%, 100%, and 110% of the empirical lookup gave positive-minus-negative deficit effects of -1620, -900, and 0 RPS-seconds, respectively. Thus the controller-decision difference under the frozen policy is real, but the claim that it necessarily creates measured Ready-capacity deficit depends on the capacity calibration. At +10%, three replicas are credited with 60.5 RPS and are treated as sufficient for the 60 RPS peak.

#### Negative finding

Positive bias did not create excess replica-seconds under the oracle-relative cost definition: both conditions recorded zero. The positive forecast requested the same four replicas as the oracle, so it was not overprovisioned relative to the reference policy. The study must not claim that every positive bias produces resource waste.

#### Defensible claim

Under the tested sustained-peak workload and baseline capacity policy, changing only the direction of a persistent 5 RPS error changed the discrete replica decision and converted equal aggregate forecast error into different operational harm. Persistent underprediction caused decision error, deficiency, higher P99, and longer composite-SLO violation; equal overprediction did not impose oracle-relative excess capacity in this pair. The measured Ready-deficit component is capacity-calibration dependent.

#### Prohibited overclaims

- Do not claim that positive bias always wastes replicas.
- Do not claim that negative bias always produces Ready-capacity deficit under every valid capacity model.
- Do not describe Holm-adjusted results as statistically significant at 0.05.
- Do not generalize beyond the tested controller, capacity boundary, sustained workload, and four-replica system.


---

## Appendix 2 - 02 Error Duration

### Evidence Ledger 02 - Forecast-Error Duration

#### Controlled contrast

- Contrast: shortened peak minus extended peak.
- Workload: `sustained-peak-v1`.
- Inferential unit: matched run repetition.
- Sample: 8 matched pairs (16 Step 15 runs).
- Aggregate-accuracy control: MAE = 2.9661 RPS and RMSE = 10.1889 RPS for both forecasts in every repetition.
- Estimand: B minus A, where A is extended peak and B is shortened peak.
- Important non-matching metric: transition MAE was 17.5 RPS for extended and 0 for shortened. Therefore this pair establishes equality of aggregate MAE/RMSE, not equality of transition-sensitive error.

#### Evidence

| Outcome | Extended (A) | Shortened (B) | Paired effect B-A | 95% paired bootstrap CI | Raw exact p | Holm p | Pair direction |
|---|---:|---:|---:|---:|---:|---:|---|
| Desired-replica MAE | 0.25 | 0.25 | 0 | [0, 0] | 1 | 1 | 8 ties |
| Deficient replica-seconds | 0 | 90 | +90 | [90, 90] | 0.0078125 | 0.1640625 | 8 positive |
| Request P99 latency | 35.04 ms | 1578.83 ms | +1543.79 ms | [1269.02, 1866.57] | 0.0078125 | 0.1640625 | 8 positive |
| Composite-SLO duration | 21 s | 27 s | +6 s | [0.25, 11.5] | 0.1015625 | 1 | 5 positive, 3 negative |
| Excess replica-seconds | 90 | 0 | -90 | [-90, -90] | 0.0078125 | 0.0546875 | 8 negative |

#### Causal interpretation

The forecasts have identical aggregate MAE and RMSE and equal absolute desired-replica error, but the decision error occurs on opposite sides of the workload event. The shortened forecast ends the peak before actual demand falls, causing a premature scale-down and 90 deficient replica-seconds. The extended forecast keeps the peak after actual demand falls, causing 90 excess replica-seconds without deficiency. The error duration/direction relative to the falling transition therefore determines whether equal decision-error magnitude becomes reliability harm or resource cost.

The large P99 difference is consistent with the readiness/capacity mechanism: premature scale-down overlaps continuing high demand, whereas late scale-down occurs after demand has already declined.

#### SLO robustness

Across latency thresholds of 200, 300, and 500 ms:

- composite-SLO mean differences remained positive at +6.125, +6.0, and +5.875 seconds;
- all leave-one-pair-out mean estimates remained positive;
- composite pair-level directions were heterogeneous (5 positive, 3 negative);
- latency-only differences were +9.375, +9.25, and +8.25 seconds, with all 8 pairs positive and raw exact p = 0.0078125.

Thus the average harm direction is robust, but universal pair-level dominance is not supported under the composite SLO. The composite definition includes completion and failure effects that can add run-level variability even when tail-latency harm is strongly consistent.

#### Safety evidence

No safety-on/off ablation was run for the shortened/extended pair. Step 20 must report the safety effect as not tested, not infer it from missed peaks or persistent bias.

#### Negative and constraining findings

1. Desired-replica MAE was identical (0.25) despite opposite operational consequences. This demonstrates that absolute decision-error magnitude also loses direction and timing information.
2. Composite-SLO duration was not consistently larger in every shortened run: 5 pairs were positive and 3 negative; raw exact p = 0.1015625.
3. Transition MAE was not matched. It distinguishes the pair, so this comparison does not show that every forecast metric fails; a transition-sensitive metric captures part of the structural difference.
4. After Holm correction, neither harm nor cost outcome crossed 0.05. The effects should be reported with magnitudes, intervals, and direction counts rather than a multiplicity-adjusted significance claim.

#### Defensible claim

For the tested sustained-peak workload, shortening versus extending a forecast peak while holding aggregate MAE and RMSE equal caused equal-magnitude replica-decision error to produce opposite consequences. Premature termination created 90 deficient replica-seconds and substantially higher request P99, whereas delayed termination created 90 excess replica-seconds. The shortened condition was worse on average for composite-SLO duration, but that SLO effect was heterogeneous across matched runs. Transition MAE distinguished the forecasts and is therefore informative for this error structure.

#### Prohibited overclaims

- Do not say shortened peaks increased composite-SLO duration in every run.
- Do not claim transition MAE was held constant.
- Do not claim safety corrects duration errors; it was not tested for this pair.
- Do not describe Holm-adjusted results as significant at 0.05.
- Do not generalize the exact 90-replica-second exchange beyond this workload duration and controller policy.


---

## Appendix 3 - 03 Event Presence

### Evidence Ledger 03 - Event Presence (Missed versus False Peak)

#### Controlled contrast

- Contrast: missed peak minus false peak.
- Workload: `narrow-spike-v1`.
- Inferential unit: matched run repetition.
- Sample: 8 matched pairs (16 Step 15 runs).
- Aggregate-accuracy control: MAE = 6.0345 RPS and RMSE = 14.5330 RPS for both forecasts in every repetition.
- Estimand: B minus A, where A is false peak and B is missed peak.
- Transition MAE was not matched: false peak = 0 and missed peak = 17.5 RPS under the frozen transition definition.

#### Evidence

| Outcome | False peak (A) | Missed peak (B) | Paired effect B-A | 95% paired bootstrap CI | Raw exact p | Holm p | Pair direction |
|---|---:|---:|---:|---:|---:|---:|---|
| Desired-replica MAE | 0.6667 | 1.0 | +0.3333 (+50%) | [0.3333, 0.3333] | 0.0078125 | 0.0546875 | 8 positive |
| Deficient replica-seconds | 0 | 180 | +180 | [180, 180] | 0.0078125 | 0.1640625 | 8 positive |
| Request P99 latency | 31.50 ms | 4836.93 ms | +4805.43 ms | [4101.49, 5503.29] | 0.0078125 | 0.1640625 | 8 positive |
| Composite-SLO duration | 12.75 s | 62 s | +49.25 s (+386.3%) | [43.375, 55.25] | 0.0078125 | 0.1640625 | 8 positive |
| Excess replica-seconds | 120 | 0 | -120 (-100%) | [-120, -120] | 0.0078125 | 0.0546875 | 8 negative |

#### Causal interpretation

The forecasts have identical aggregate MAE and RMSE, but place the same broad error budget on opposite event-presence mistakes. A missed peak withholds scale-out during real high demand, producing 180 deficient replica-seconds, multi-second request P99, and prolonged SLO harm. A false peak requests capacity for demand that never occurs, producing 120 excess replica-seconds without measured deficiency. Within this controlled pair, event presence causally determines whether aggregate error becomes reliability harm or resource cost.

#### Robustness

##### SLO definition

Missed-minus-false SLO duration remained positive in all six tested definitions:

- composite SLO: +49.25 s at 200 and 300 ms; +49.125 s at 500 ms;
- latency-only: +33.5 s at 200 and 300 ms; +32.75 s at 500 ms.

Every matched pair and every leave-one-pair-out estimate retained the same direction; raw exact p = 0.0078125 in every scenario.

##### Capacity accounting

Missed-minus-false Ready-capacity deficit remained positive under all capacity factors:

- 90% lookup: +1200.75 RPS-s;
- baseline lookup: +1183.125 RPS-s;
- 110% lookup: +1120.5 RPS-s.

All eight pairs and every leave-one-pair-out estimate retained the direction. This asymmetry is not an artifact of the baseline Pod-capacity estimate.

#### Safety evidence

For missed peaks, safety on versus off (5 matched pairs) changed:

- desired-replica MAE: 1.0 to 0.2 (-80%);
- deficient replica-seconds: 180 to 21 (-159; -88.3%);
- request P99: 5197.66 to 2697.31 ms (-2500.35 ms; -48.1%), 95% CI [-3175.03, -1825.67];
- composite-SLO duration: 60 to 15 s (-45 s; -75%), 95% CI [-47.405, -42.2];
- excess replica-seconds: 0 to 15 (+15).

All five pairs agreed on every listed harm reduction and on added excess capacity. Exact two-sided p = 0.0625, the minimum possible with five pairs; Holm-adjusted harm p = 0.375.

Safety reduced but did not eliminate harm: 21 deficient replica-seconds, approximately 2.7 s request P99, and 15 SLO seconds remained on average. Reactive intervention begins only after observed overload persists and new capacity still requires readiness time.

#### Safety-threshold robustness

In the Step 19 replacement campaign, increasing overload persistence from 1 to 3 seconds for missed peaks:

- added 2.8 SLO seconds, 95% CI [1.2, 4.2];
- added 61 Ready-capacity-deficit RPS-s, CI [43, 82];
- added 1269.66 ms request P99, CI [703.38, 1872.82];
- used 5.8 fewer deployment replica-seconds, CI [-6.0, -5.4].

Thus faster intervention improves protection at a small capacity premium. Safety performance is conditional on the frozen trigger persistence and readiness delay.

#### Negative and constraining findings

1. Safety did not prevent initial harm and did not restore the missed-peak run to false-peak behavior.
2. Safety added capacity cost; it converted rather than erased part of the consequence.
3. Transition MAE distinguished the pair, so aggregate MAE/RMSE are not the only available forecast diagnostics.
4. With five pairs, safety effects cannot meet conventional two-sided p<0.05.
5. False peaks are not harmless: their principal observed consequence was 120 excess replica-seconds, not SLO harm.

#### Defensible claim

For the tested narrow-spike workload, equal-MAE/RMSE missed and false peaks caused a robust harm-versus-cost asymmetry. Missing a real event produced severe deficient capacity, tail latency, and SLO duration, whereas predicting a nonexistent event primarily produced excess replica cost. The fixed reactive safety rule corrected most but not all missed-peak harm and exchanged that protection for additional capacity. This direction survived all tested SLO definitions, capacity assumptions, and leave-one-pair-out checks.

#### Prohibited overclaims

- Do not call false peaks operationally harmless; they incur resource cost.
- Do not say safety eliminated missed-peak harm.
- Do not claim safety was conventionally significant at p<0.05 with five pairs.
- Do not claim MAE/RMSE were the only metrics examined; transition MAE distinguished the pair.
- Do not generalize the exact effects beyond the tested spike, controller, four-replica bound, and cluster.


---

## Appendix 4 - 04 Error Timing

### Evidence Ledger 04 - Forecast-Error Timing and Workload Interaction

#### Controlled contrasts

Two accuracy-matched early/late contrasts were analyzed separately:

1. periodic workload (`pair-06-timing_periodic`), 8 matched pairs;
2. narrow spike (`pair-07-timing_spike`), 8 matched pairs.

The estimand is late minus early. MAE and RMSE were exactly equal within each workload:

- periodic: MAE 6.5294 RPS; RMSE 7.3618 RPS;
- narrow spike: MAE 4.0230 RPS; RMSE 11.8661 RPS.

Transition MAE was almost equal for periodic traffic (7.6533 early versus 7.6679 late), but strongly distinguished the narrow spike (0 early versus 35 RPS late).

#### Periodic-workload evidence

| Outcome | Early | Late | Late-early effect | 95% paired bootstrap CI | Raw exact p | Holm p |
|---|---:|---:|---:|---:|---:|---:|
| Desired-replica MAE | 0.4583 | 0.4583 | 0 | [0, 0] | 1 | 1 |
| Deficient replica-seconds | 165 | 165 | 0 | [0, 0] | 1 | 1 |
| Excess replica-seconds | 165 | 165 | 0 | [0, 0] | 1 | 1 |
| Request P99 latency | 30.68 ms | 34.08 ms | +3.40 ms | [1.95, 4.91] | 0.0078125 | 0.1640625 |
| Composite-SLO duration | 104.375 s | 107 s | +2.625 s | [-1.625, 6.75] | 0.3515625 | 1 |

Periodic early and late forecasts produced identical replica-error, deficiency, and excess-capacity summaries. The P99 effect was small in absolute terms, and the SLO effect was uncertain and directionally heterogeneous (5 positive, 3 negative).

#### Narrow-spike evidence

| Outcome | Early | Late | Late-early effect | 95% paired bootstrap CI | Raw exact p | Holm p |
|---|---:|---:|---:|---:|---:|---:|
| Desired-replica MAE | 0.3333 | 0.3333 | 0 | [0, 0] | 1 | 1 |
| Deficient replica-seconds | 30 | 30 | 0 | [0, 0] | 1 | 1 |
| Excess replica-seconds | 30 | 30 | 0 | [0, 0] | 1 | 1 |
| Request P99 latency | 29.95 ms | 2595.46 ms | +2565.51 ms | [2233.30, 2954.57] | 0.0078125 | 0.1640625 |
| Composite-SLO duration | 11.25 s | 19.875 s | +8.625 s (+76.7%) | [4.5, 13.5] | 0.0078125 | 0.1640625 |

All eight narrow-spike pairs showed higher P99 and longer SLO duration for the late forecast, despite identical absolute desired-replica error and identical deficient/excess desired-replica seconds.

#### Identified workload interaction

The prespecified difference-in-differences was `(late-early)_spike - (late-early)_periodic`.

- P99 interaction: +2562.12 ms, 95% CI [2226.89, 2953.05], raw p = 0.0078125, Holm-adjusted p = 0.0234375, all 8 blocks positive.
- SLO-duration interaction: +6.0 s, CI [-1.25, 13.125], raw p = 0.15625, Holm-adjusted p = 0.3125.
- Desired-replica MAE, deficient replica-seconds, and excess replica-seconds interactions were exactly zero.

The P99 interaction is the clearest multiplicity-adjusted inferential result in the study: the operational effect of lateness was substantially larger for a narrow spike than for periodic traffic.

#### Causal mechanism

For the narrow spike, early forecasting places the scale-out request before the short demand event, allowing capacity to become Ready before or near onset. Late forecasting shifts the same broad error magnitude after onset; the remaining lead time is shorter than readiness delay, so requests encounter insufficient Ready capacity during the most consequential seconds. Absolute desired-replica error integrates the shifted trajectories and is identical, but does not encode whether capacity was Ready when the spike arrived.

Periodic traffic repeatedly revisits similar demand states and has broader/repeated transitions. Shifting the forecast early or late produced the same aggregate controller trajectory and allowed later cycles and existing replicas to dilute the timing consequence. This mechanism is supported within the tested workloads; it should not be generalized to every periodic process without further experiments.

#### SLO robustness

For the narrow spike, late-minus-early SLO duration remained positive under all tested definitions:

- composite: +8.625 s at 200, 300, and 500 ms;
- latency-only: +8.75, +8.75, and +7.875 s at 200, 300, and 500 ms.

All eight pairs and every leave-one-pair-out estimate retained the direction.

For periodic traffic, latency-only differences were 0, -0.125, and 0 seconds across the thresholds, and composite differences were only +2.625 to +2.75 seconds with mixed pair directions. Therefore, a general claim that late forecasts are always worse is not supported.

#### Forecast-horizon robustness

Step 19 prospectively compared 3 s and 9 s horizons for the narrow-spike pair (5 matched pairs per early/late side).

For late forecasts, increasing horizon from 3 to 9 s:

- reduced SLO duration by 16.2 s, CI [-21.8, -10.6];
- reduced request P99 by 1080.50 ms, CI [-1535.24, -544.70];
- reduced Ready-capacity deficit by 216 RPS-s, CI [-242, -179];
- reduced deficient replica-seconds by 17.4, CI [-18, -16.2].

All five pairs agreed; exact p = 0.0625 for these nonzero effects.

For early forecasts, 9 s versus 3 s reduced SLO duration by 7.8 s and P99 by 4.75 ms, while deficiency remained exactly zero. Horizon therefore moderated both sides but delivered a much larger capacity/readiness benefit for late forecasts.

#### Safety evidence

No direct safety on/off ablation was performed for the early/late pair. Safety effects from missed peaks cannot be assigned to timing errors without data. The horizon experiment is the relevant prospective timing robustness check.

#### Negative and constraining findings

1. Periodic early and late forecasts produced identical replica decisions and capacity summaries.
2. Narrow-spike early and late forecasts also had identical absolute desired-replica error and deficient/excess desired-replica seconds, even while latency differed by seconds.
3. Periodic SLO differences were small, mixed, and non-significant.
4. Transition MAE detected late narrow-spike placement but provided almost no separation for the periodic pair.
5. Direct safety correction of early/late timing was not tested.

#### Defensible claim

Forecast timing had a workload-dependent causal effect. With matched MAE/RMSE, late versus early prediction produced little operational difference for the tested periodic workload but caused severe P99 and SLO harm for a narrow spike. The identified P99 interaction was +2562 ms and survived Holm correction. The mechanism was lead time relative to readiness: late spike forecasts requested capacity too close to or after demand onset, whereas early forecasts allowed capacity to become Ready. A longer horizon substantially reduced this harm. Aggregate desired-replica error did not capture the readiness-timing consequence.

#### Prohibited overclaims

- Do not state that late forecasts are always worse across workloads.
- Do not claim early/late timing changed aggregate replica-error magnitude in these pairs.
- Do not infer a direct safety effect for timing; it was not tested.
- Do not interpret ranking or cross-workload associations as the causal evidence; the matched contrasts and interaction are the causal evidence.


---

## Appendix 5 - 05 Error Placement

### Evidence Ledger 05 - Stable versus Transition-Period Error Placement

#### Controlled contrast

- Contrast: transition-period error minus stable-period error.
- Workload: `gradual-ramp-v1`.
- Inferential unit: matched run repetition.
- Sample: 8 matched pairs (16 Step 15 runs).
- Aggregate-accuracy control: MAE = 1.0127 RPS and RMSE = 2.8463 RPS for both conditions in every repetition.
- Estimand: B minus A, where A is stable-period error and B is transition-period error.
- Transition MAE intentionally differs: 0 RPS for stable placement and 1.6 RPS for transition placement.

#### Evidence

| Outcome | Stable (A) | Transition (B) | Paired effect B-A | 95% paired bootstrap CI | Raw exact p | Holm p | Pair direction |
|---|---:|---:|---:|---:|---:|---:|---|
| Transition MAE | 0 | 1.6 RPS | +1.6 | [1.6, 1.6] | 0.0078125 | 0.1640625 | 8 positive |
| Desired-replica MAE | 0.1146 | 0.1375 | +0.0229 (+20%) | [0.0229, 0.0229] | 0.0078125 | 0.0546875 | 8 positive |
| Deficient replica-seconds | 0 | 0 | 0 | [0, 0] | 1 | 1 | 8 ties |
| Excess replica-seconds | 55 | 66 | +11 (+20%) | [11, 11] | 0.0078125 | 0.0546875 | 8 positive |
| Request P99 latency | 32.98 ms | 31.81 ms | -1.17 ms | [-2.98, 0.26] | 0.25 | 1 | 4 negative, 4 positive |
| Composite-SLO duration | 64.75 s | 63.125 s | -1.625 s | [-5.75, 2.0] | 0.4921875 | 1 | 4 negative, 4 positive |

#### Causal interpretation

With aggregate MAE and RMSE held equal, moving the error into the gradual workload transition caused a deterministic increase in transition MAE, a small increase in absolute replica-decision error, and 11 additional excess replica-seconds. It did not create deficient capacity. Under the tested mutation and controller thresholds, the affected transition decisions remained on the overprovisioning side of the oracle rather than delaying capacity needed by demand.

The operational effect was therefore additional resource cost, not reliability harm. P99 and SLO differences were small, crossed zero, and split evenly in direction across repetitions.

#### SLO robustness

At 200, 300, and 500 ms:

- the composite transition-minus-stable difference was -1.625 s;
- pair directions were evenly split (4 negative, 4 positive);
- raw exact p = 0.4921875;
- latency-only SLO duration was zero for both conditions in every run.

The leave-one-pair-out composite mean remained slightly negative, but this does not overcome the pair heterogeneity, zero latency-only violations, or interval spanning zero. It is not evidence that transition placement improves reliability.

#### Safety evidence

No safety on/off experiment was run for this pair. The absence of deficiency suggests the overload-trigger safety rule may have had little opportunity to act, but that is a mechanism-based expectation, not an observed safety result.

#### Negative and constraining findings

1. Transition placement did not cause deficient replica capacity.
2. It did not reproduce a meaningful P99 or SLO penalty.
3. P99 and composite-SLO pair directions were exactly split.
4. Latency-only SLO duration was zero for both conditions at all tested thresholds.
5. Transition MAE correctly identified transition placement and aligned with a small decision/cost change, making it useful here where aggregate MAE/RMSE were tied.
6. No outcome crossed the prespecified Holm-adjusted 0.05 threshold; decision and cost outcomes reached 0.0546875.

#### Defensible claim

For the tested gradual-ramp workload, placing an equal-MAE/RMSE error at the transition rather than a stable period caused a small, deterministic increase in replica-decision error and 11 excess replica-seconds, but no deficient capacity and no reproducible latency or SLO harm. Transition MAE distinguished the placement difference. This result constrains the broader hypothesis: transition-localized error is not inherently harmful; its consequence depends on error direction, threshold crossing, and whether the affected decision creates under- or overprovisioning.

#### Prohibited overclaims

- Do not claim transition placement generally worsens SLO reliability.
- Do not interpret the small negative mean P99/SLO differences as a protective effect.
- Do not infer safety behavior; it was not tested.
- Do not generalize from one gradual-ramp mutation to all transition errors.


---

## Appendix 6 - 06 Error Shape

### Evidence Ledger 06 - Forecast Shape (Sharpened versus Smoothed)

#### Controlled contrast

- Contrast: smoothed minus sharpened forecast shape.
- Workload: `periodic-triangle-v1`.
- Inferential unit: matched run repetition.
- Sample: 8 matched pairs (16 Step 15 runs).
- Accuracy controls were effectively exact: MAE = 0.29956 RPS, RMSE = 0.72668 RPS, and transition MAE = 0.33866 RPS for both conditions.
- Estimand: B minus A, where A is sharpened and B is smoothed.

#### Evidence

| Outcome | Sharpened (A) | Smoothed (B) | Paired effect B-A | 95% paired bootstrap CI | Raw exact p | Holm p | Pair direction |
|---|---:|---:|---:|---:|---:|---:|---|
| Desired-replica MAE | 0 | 0 | 0 | [0, 0] | 1 | 1 | 8 ties |
| Deficient replica-seconds | 0 | 0 | 0 | [0, 0] | 1 | 1 | 8 ties |
| Excess replica-seconds | 0 | 0 | 0 | [0, 0] | 1 | 1 | 8 ties |
| Request P99 latency | 30.85 ms | 30.43 ms | -0.42 ms | [-2.05, 0.81] | 0.7578125 | 1 | 2 positive, 6 negative |
| Composite-SLO duration | 104.0 s | 104.5 s | +0.5 s | [-2.5, 3.75] | 0.8515625 | 1 | 4 positive, 4 negative |

#### Causal interpretation

The shape mutation did not move the forecast across any replica-decision boundary under the tested periodic workload and controller policy. Consequently, sharpened and smoothed forecasts generated the same desired-replica trajectory as the oracle and the same capacity outcomes. Once controller actions are identical, small run-to-run P99 and SLO differences are attributable to experimental variability rather than the controlled shape mutation.

This is not evidence that forecast shape can never matter. It shows that shape differences below the controller's decision-resolution boundary can be operationally equivalent.

#### SLO robustness

Across 200, 300, and 500 ms thresholds:

- composite smoothed-minus-sharpened differences were only +0.625, +0.5, and +0.5 s;
- pair directions were split 4 positive and 4 negative;
- leave-one-pair-out means crossed direction;
- latency-only SLO duration was zero for both conditions at 300 and 500 ms;
- at 200 ms, only one smoothed run contributed one latency-only violation second.

The negative result is robust to the tested SLO definitions.

#### Safety evidence

No safety on/off ablation was run for the shape pair. Because the forecasts produced no deficient replica-seconds, there is no observed overload harm for safety to correct. It remains incorrect to report a safety treatment effect without a direct ablation.

#### Metric interpretation

This pair is a case where conventional metrics did not mislead operationally: MAE, RMSE, and transition MAE were tied, and controller/action outcomes were also tied. The metrics did not identify the visual shape difference, but that distinction was irrelevant to this controller because it did not cross a decision threshold.

The defensible conclusion is not that MAE/RMSE predicted latency precisely. Rather, they correctly failed to rank two forecasts whose controlled shape difference produced no reproducible decision or operational difference.

#### Negative and constraining findings

1. Shape alone did not alter replica decisions.
2. There was no deficiency or excess-capacity difference.
3. P99 difference was less than 1 ms and its interval crossed zero.
4. Composite-SLO difference was 0.5 s with exactly split pair directions.
5. No comparison approached statistical reliability.
6. All three forecast-error metrics were equal and the operational outcomes were effectively equal.

#### Defensible claim

For the tested periodic-triangle workload, sharpened and smoothed forecasts with equal MAE, RMSE, and transition MAE produced identical replica decisions and capacity outcomes, with no reproducible latency or SLO difference. The shape mutation remained within the same replica-decision regions. This negative result bounds the study's contribution: forecast structure matters operationally when it changes threshold crossings, event lead time, or readiness, not merely because two traces have visibly different shapes.

#### Prohibited overclaims

- Do not claim forecast shape never matters.
- Do not claim MAE/RMSE predict request latency from this pair.
- Do not interpret sub-millisecond P99 variation as a treatment effect.
- Do not infer a safety effect without a direct ablation.


---

## Appendix 7 - 07 Reactive Safety Net

### Evidence Ledger 07 - Reactive Safety-Net Research Question

#### Research question

How does a fixed reactive safety mechanism change the operational impact of different forecast-error structures?

#### Controlled design

- Directly tested errors: persistent negative bias (`sustained-peak-v1`) and missed peak (`narrow-spike-v1`).
- Comparison: identical workload and forecast replayed safety off versus safety on.
- Inferential unit: matched run repetition.
- Sample: 5 matched pairs per error (20 runs across off/on comparators).
- Forecast MAE, RMSE, and transition MAE are exactly unchanged by safety.
- Step 16 controller: v1.1.1. Step 19 persistence robustness replacements used reliability-amended v1.1.2 and were analyzed as a separate block, not pooled.

#### Fixed mechanism

1. Observe finalized dispatched requests in one-second windows.
2. Estimate Ready capacity with the fixed 1->30, 2->40, 3->55, 4->65 RPS lookup.
3. Mark overload when observed demand exceeds estimated Ready capacity.
4. Trigger after two consecutive overload windows.
5. Raise the safety floor to the minimum replicas required by observed demand.
6. Issue `max(predictive command, safety floor)` through a single arbiter/writer.
7. Release after protection need clears and a fixed 30-second hold expires.
8. Missing observations are logged and never inferred as overload.

The rule, thresholds, capacity lookup, and release behavior were identical across both tested error types.

#### Persistent-negative-bias effect

| Outcome | Safety off | Safety on | On-off effect | 95% paired bootstrap CI | Raw exact p | Holm p | Pair direction |
|---|---:|---:|---:|---:|---:|---:|---|
| Desired-replica MAE | 0.5861 | 0.0667 | -0.5194 (-88.6%) | [-0.5194, -0.5194] | 0.0625 | 0.125 | 5 negative |
| Deficient replica-seconds | 211 | 7 | -204 (-96.7%) | [-204, -204] | 0.0625 | 0.375 | 5 negative |
| Request P99 | 48.72 ms | 33.03 ms | -15.69 ms (-32.2%) | [-19.44, -11.94] | 0.0625 | 0.375 | 5 negative |
| Composite-SLO duration | 26.4 s | 17.2 s | -9.2 s (-34.8%) | [-18.8, 3.0] | 0.1875 | 0.375 | 4 negative, 1 positive |
| Oracle-relative excess replica-seconds | 0 | 17 | +17 | [17, 17] | 0.0625 | 0.125 | 5 positive |

Step 16 controller-cost accounting found 221 additional requested replica-seconds per run (1,105 total) and no additional net action transitions. This differs from the +17 oracle-relative excess metric: the first compares total safety-on versus safety-off requested occupancy, while the second compares requested replicas with the oracle. They answer different cost questions and must not be substituted.

Safety reduced aggregate Step 16 harm from 132 to 86 seconds (46 avoided; 34.8%), but one repetition increased from 13 to 26 harm seconds. All harm in these runs arose from the one-second completion-ratio component rather than P99 or failure-rate violation seconds.

#### Missed-peak effect

| Outcome | Safety off | Safety on | On-off effect | 95% paired bootstrap CI | Raw exact p | Holm p | Pair direction |
|---|---:|---:|---:|---:|---:|---:|---|
| Desired-replica MAE | 1.0 | 0.2 | -0.8 (-80%) | [-0.8, -0.8] | 0.0625 | 0.125 | 5 negative |
| Deficient replica-seconds | 180 | 21 | -159 (-88.3%) | [-159, -159] | 0.0625 | 0.375 | 5 negative |
| Request P99 | 5197.66 ms | 2697.31 ms | -2500.35 ms (-48.1%) | [-3175.03, -1825.67] | 0.0625 | 0.375 | 5 negative |
| Composite-SLO duration | 60 s | 15 s | -45 s (-75%) | [-47.405, -42.2] | 0.0625 | 0.375 | 5 negative |
| Oracle-relative excess replica-seconds | 0 | 15 | +15 | [15, 15] | 0.0625 | 0.125 | 5 positive |

Step 16 controller-cost accounting found 174 additional requested replica-seconds and 2 additional scaling actions per run (870 replica-seconds and 10 actions total). Again, this is a safety-on minus safety-off occupancy premium, whereas +15 is oracle-relative excess.

#### Intervention and readiness evidence

- Every safety-on run generated exactly one intervention and one clean release.
- First intervention sequence was 61 in every run.
- Maximum request was four replicas.
- Missed-peak readiness delays ranged from 1 to 6 s (mean 3.4 s).
- Persistent-bias readiness delay was 1 s in every run.
- Missed peaks retained 10-15 post-intervention harm seconds per run.

The logs support the mechanism: safety cannot protect the pre-detection window, and requested replicas cannot protect traffic until they become Ready. These delays explain residual harm without requiring a speculative mechanism.

#### Safety-by-error interaction

The identified interaction is `(safety on-off)_missed - (safety on-off)_persistent-negative-bias` over five matched blocks.

- P99 benefit was 2484.66 ms larger for missed peaks, CI [-3155.83, -1813.49], exact p = 0.0625, Holm p = 0.1875.
- SLO reduction was 35.8 s larger for missed peaks, CI [-49.4, -26.8], exact p = 0.0625, Holm p = 0.1875.
- The deficient-replica reduction differed by +45 replica-seconds under the frozen interaction orientation; percentage protection was 88.3% for missed peaks and 96.7% for persistent bias. Absolute interaction signs must be interpreted alongside different off baselines.
- Missed peaks added 2 fewer oracle-relative excess replica-seconds than persistent bias.

Safety had a much larger latency/SLO benefit for missed peaks because the predictive controller supplied no event protection. For persistent bias, predictive control was already partially responsive and baseline P99 was low, leaving less latency harm to avoid while the safety floor remained active longer.

#### Robustness

##### SLO and capacity accounting

Offline analysis showed safety benefit for missed peaks under all six SLO definitions and all three capacity factors. Persistent-bias capacity benefit disappeared under the optimistic +10% capacity accounting because three replicas were treated as sufficient for 60 RPS.

##### Trigger persistence

Step 19 prospectively compared 1 s versus 3 s persistence for missed peaks using controller v1.1.2 (5 matched pairs). Increasing persistence to 3 s:

- added 2.8 SLO seconds, CI [1.2, 4.2];
- added 61 Ready-deficit RPS-s, CI [43, 82];
- added 1269.66 ms P99, CI [703.38, 1872.82];
- saved 5.8 deployment replica-seconds, CI [-6.0, -5.4].

Thus faster detection improves protection at a small resource premium; the qualitative trade-off persists, but its magnitude is threshold-dependent.

#### Combined Step 16 operational accounting

Across all ten safety pairs:

- harm fell from 432 to 161 seconds;
- avoided harm = 271 seconds (62.7% aggregate reduction);
- additional requested replica-seconds = 1,975;
- additional scaling actions = 10;
- mean readiness delay = 2.2 s.

This combined total is descriptive across two different errors and workloads; it is not a single pooled causal effect for a broader population.

#### Statistical interpretation

With five pairs, the smallest possible two-sided exact p is 0.0625. None of the safety effects can cross p<0.05 under this design, and Holm-adjusted p-values are larger. The evidence is best described as large, consistently directed practical protection for deficiency and P99, with limited exact-test resolution. Persistent-bias SLO duration is additionally heterogeneous and its interval includes zero.

#### Negative and constraining findings

1. Safety did not eliminate harm in either tested error.
2. One persistent-bias repetition had greater SLO harm with safety on.
3. Persistent-bias SLO uncertainty included zero.
4. Safety always added capacity under the analyzed cost metrics.
5. Missed peaks added command transitions; persistent bias changed occupancy/timing without adding net transitions.
6. A slower trigger saved a small amount of capacity but caused greater residual harm.
7. Only two underprediction structures were directly tested; false peaks, early/late timing, duration, placement, and shape received no direct safety ablation.
8. The experimental dispatched-demand signal may not be available with identical latency in production telemetry.

#### Answer to the secondary RQ

The fixed reactive safety mechanism changed underprediction errors by raising a replica floor after observed overload, thereby converting much of decision deficiency and SLO harm into additional requested capacity. It was most effective for missed peaks, reducing deficient replica-seconds by 88.3%, request P99 by 48.1%, and SLO duration by 75%, while adding capacity and two action transitions per run. For persistent negative bias, it reduced deficiency by 96.7% and P99 by 32.2%, but SLO reduction was smaller and heterogeneous, and the capacity floor remained active longer. Detection persistence and Pod readiness caused residual harm; a faster trigger improved protection at a modest additional replica-second cost. These conclusions are causal for the two replayed errors under the fixed rule, not for forecast errors generally.

#### Prohibited overclaims

- Do not say safety makes forecast quality unimportant.
- Do not say safety eliminates underprediction harm.
- Do not describe five-pair effects as conventionally significant at p<0.05.
- Do not combine total requested replica premium with oracle-relative excess without naming the denominator.
- Do not generalize the safety effect to error types that were not directly replayed.
- Do not generalize the dispatch-signal timing or capacity lookup to production systems without validation.


---

## Appendix 8 - 08 Metric Usefulness And Rankings

### Evidence Ledger 08 - Metric Usefulness and Ranking Agreement

#### Purpose and evidence status

This section answers when aggregate forecast metrics are informative, when they fail, and whether forecast, decision, and operational rankings are interchangeable.

Two evidence types must remain separate:

1. Controlled accuracy-matched pairs establish causal differences that MAE/RMSE cannot distinguish within those pairs.
2. Correlations across 14 condition medians are supplementary associations; they do not establish that one metric causes or predicts another outside this dataset.

#### Controlled evidence: where aggregate metrics fail

MAE and RMSE were equal by design within all seven primary contrasts, yet large operational differences occurred in several:

- positive versus negative bias: 211 deficient replica-seconds and 12.86 ms P99 difference;
- shortened versus extended: 90 deficient versus 90 excess replica-seconds and 1543.79 ms P99 difference;
- missed versus false peak: 180 deficient versus 120 excess replica-seconds and 4805.43 ms P99 difference;
- late versus early narrow spike: identical replica-error summaries but 2565.51 ms P99 and 8.625 s SLO differences.

These controlled comparisons establish that equal MAE/RMSE is insufficient to infer equal operational consequence when error direction, event presence, duration, or lead time differs.

#### Controlled evidence: where tied metrics were appropriate

##### Shape pair

Sharpened and smoothed forecasts had equal MAE, RMSE, and transition MAE and produced identical controller decisions, deficiency, and excess capacity. Their P99 and SLO differences were negligible and uncertain. Here, tied conventional metrics appropriately corresponded to operational equivalence under the controller.

##### Periodic timing pair

Equal early/late MAE and RMSE corresponded to identical desired-replica MAE, deficiency, and excess capacity. P99 differed by only 3.40 ms and composite-SLO uncertainty included zero. Conventional metrics were not sufficient to explain every millisecond, but their tie did not conceal a material controller/capacity difference in this workload.

Thus MAE/RMSE do not always fail; they fail when the omitted structure changes a decision boundary or readiness timing.

#### Transition MAE usefulness and limitations

Transition MAE identified several structures hidden by aggregate MAE/RMSE:

- extended versus shortened peak: 17.5 versus 0 RPS;
- missed versus false peak: 17.5 versus 0 RPS;
- transition versus stable placement: 1.6 versus 0 RPS;
- late versus early narrow spike: 35 versus 0 RPS.

It correctly flagged transition/event-placement differences that were operationally meaningful in the duration, missed-peak, and late-spike comparisons. It also flagged transition placement when the result was only 11 excess replica-seconds and no SLO harm. Therefore transition MAE is more structurally sensitive, but a high value is not itself proof of harm.

For periodic early/late timing, transition MAE differed by only 0.0146 RPS and operational differences were small. For sharpened/smoothed shape, it tied and outcomes tied.

#### Ranking agreement across 14 condition medians

Selected associations:

| Metric pair | Spearman rho | Kendall tau-b | Top-one agreement | Pairwise disagreement |
|---|---:|---:|---|---:|
| MAE - desired-replica MAE | 0.786 | 0.686 | No | 14.6% |
| RMSE - desired-replica MAE | 0.749 | 0.588 | No | 19.5% |
| Desired-replica MAE - deficient replica-seconds | 0.718 | 0.645 | No | 13.4% |
| MAE - deficient replica-seconds | 0.635 | 0.490 | No | 21.5% |
| RMSE - request P99 | 0.427 | 0.375 | No | 30.6% |
| MAE - request P99 | 0.257 | 0.229 | No | 38.1% |
| RMSE - SLO duration | -0.573 | -0.443 | No | 72.9% |
| MAE - SLO duration | -0.097 | -0.183 | Yes | 59.5% |
| Request P99 - SLO duration | -0.319 | -0.231 | No | 61.5% |
| Deficient - excess replica-seconds | -0.049 | -0.056 | No | 53.6% |

#### Interpretation of useful associations

- MAE and RMSE were reasonably aligned with average desired-replica error across conditions.
- Desired-replica MAE was strongly aligned with deficient replica-seconds.
- MAE showed moderate alignment with deficiency.
- RMSE showed moderate, not strong, alignment with request P99.

These results show that conventional accuracy can be useful for coarse condition-level screening, particularly for controller-decision error. It should not be discarded.

#### Interpretation of disagreement

- Forecast rankings did not reproduce tail-latency, SLO-duration, or excess-capacity rankings reliably.
- RMSE and composite-SLO duration were negatively associated in this condition set, demonstrating that larger squared forecast error did not imply greater measured composite harm.
- P99 and SLO duration also disagreed because P99 measures tail magnitude while SLO duration counts violating seconds and includes failure/completion components.
- Deficiency and excess capacity describe opposite cost/harm directions and were essentially uncorrelated.

Top-one agreement alone is insufficient. MAE and SLO duration shared a top-ranked condition through ties while disagreeing on 59.5% of comparable pair orderings and having near-zero/negative rank correlation.

#### SLO-ranking robustness

Changing the numerical latency threshold within the composite SLO preserved rankings:

- 200 ms: Spearman 1.0, Kendall 1.0, top-one agreement yes, 0 pairwise disagreement;
- 500 ms: Spearman 0.9989, Kendall 0.9945, top-one agreement yes, 0 pairwise disagreement among comparable pairs.

Changing the construct to latency-only did not preserve rankings:

- Spearman versus baseline composite = -0.1254;
- Kendall = -0.0699;
- top-one agreement absent;
- 55.6% pairwise disagreement.

Thus conclusions about SLO rankings are robust to the threshold within the composite construct but not to replacing the construct itself.

#### Negative and constraining findings

1. Aggregate metrics performed appropriately for the shape pair and approximately for periodic timing.
2. Transition MAE was informative but did not map monotonically to harm.
3. MAE/RMSE had useful associations with decision error; they are incomplete, not useless.
4. Top-one agreement can coexist with broad ranking disagreement.
5. Condition-level analysis contains only 14 units and many ties.
6. Ranking correlations are not causal evidence and should not be used to explain the controlled mechanisms.
7. The negative RMSE-SLO association is dataset-specific and not evidence that improving RMSE worsens reliability.

#### Defensible metric claim

MAE and RMSE provide useful coarse information about forecast magnitude and are moderately to strongly associated with replica-decision error across the tested conditions, but they are insufficient for operational ranking when error direction, event presence, duration, or readiness timing differs. Transition MAE detects several important event-local structures, yet it also cannot determine whether a transition error becomes deficiency, excess cost, or no material harm. Operational evaluation therefore requires a metric set spanning forecast error, decision error, Ready-capacity deficiency, tail magnitude, SLO duration, and resource excess rather than a single universal score.

#### Prohibited overclaims

- Do not say MAE and RMSE are useless.
- Do not interpret rank correlations as causal or predictive validation outside the 14 conditions.
- Do not say transition MAE is universally superior.
- Do not combine P99 magnitude and SLO duration as interchangeable reliability measures.
- Do not infer that higher RMSE improves SLO outcomes from the negative association.


---

## Appendix 9 - 09 Main And Primary Rq Answers

### Evidence Ledger 09 - Answers to the Main and Primary Research Questions

#### Main research question

**When workload forecasts have similar conventional accuracy, why do they produce different Kubernetes scaling decisions, SLO violations, and resource costs?**

##### Direct answer

Forecasts with similar or identical MAE/RMSE produced different outcomes when their errors occupied different operational positions relative to discrete replica thresholds, workload events, and Pod-readiness time. MAE and RMSE aggregate error magnitude across time and remove the sign, event identity, temporal placement, and remaining lead time that determine whether the controller requests too few replicas, requests too many, or requests the correct count too late to become Ready.

The controlled experiments identify three principal pathways:

1. **Decision-boundary pathway:** error direction changes whether predicted demand crosses a replica threshold. Persistent -5 RPS bias selected too few replicas at a 60 RPS sustained peak, while +5 RPS bias selected the oracle count despite identical MAE/RMSE.
2. **Harm-versus-cost pathway:** equal error budgets before versus after an event generate underprovisioning or overprovisioning. Shortened peaks and missed events caused deficiency; extended and false peaks caused excess occupancy.
3. **Readiness-timing pathway:** equal aggregate decision error can occur at operationally different times. Early and late narrow-spike forecasts had identical desired-replica error, but late requests arrived with insufficient readiness lead time and produced multi-second P99 latency.

Forecast structure did not matter when it remained inside the same decision regions. Sharpened and smoothed forecasts produced identical actions and outcomes; periodic early and late forecasts produced identical capacity summaries. Therefore, the mechanism is not structural difference by itself. It is structural difference that changes threshold crossing, under/over direction, or readiness at an important event.

##### Evidence strength

- Seven controlled accuracy-matched contrasts, 8 matched pairs each.
- Large raw exact effects for direction, duration, event presence, and narrow-spike timing.
- After Holm adjustment over prespecified domains, most individual primary effects did not cross 0.05.
- The P99 timing-by-workload interaction did survive Holm correction: +2562.12 ms, 95% CI [2226.89, 2953.05], adjusted p = 0.0234375.
- Effects are supported primarily by controlled contrast, magnitude, interval, pair consistency, and robustness—not by isolated p-values.

##### Scope

The answer applies to the tested predictive controller, empirical capacity lookup, one-to-four replica range, selected workloads, six-second baseline horizon, and Azure/K3s benchmark environment. It does not establish universal behavior for every autoscaler or application.

#### Primary research question

**When MAE and RMSE are held approximately constant, how do forecast-error direction, timing, duration, shape, and transition location affect Kubernetes scaling decisions, capacity readiness, tail-latency SLOs, and resource waste?**

#### Direction

##### Tested

Persistent -5 RPS versus +5 RPS bias on a sustained-peak workload, with MAE = RMSE = transition MAE = 5 RPS in both conditions.

##### Observed magnitude

Positive minus negative bias:

- desired-replica MAE: -0.5861;
- deficient replica-seconds: -211;
- request P99: -12.86 ms, CI [-14.75, -10.79];
- composite-SLO duration: -8.25 s, CI [-13.625, -3.5];
- excess replica-seconds: 0.

##### Mechanism and boundary

Negative bias fell below the three-to-four replica boundary at the 60 RPS peak; positive bias matched the oracle decision. Ready-deficit magnitude disappeared under optimistic +10% capacity accounting, so the capacity-harm claim is calibration-dependent. Positive bias did not create resource waste in this pair.

#### Duration

##### Tested

Shortened versus extended sustained peak, with MAE 2.9661 RPS and RMSE 10.1889 RPS in both conditions.

##### Observed magnitude

Shortened minus extended:

- desired-replica MAE: 0 difference (0.25 each);
- deficient replica-seconds: +90;
- request P99: +1543.79 ms, CI [1269.02, 1866.57];
- composite-SLO duration: +6 s, CI [0.25, 11.5], with 5 positive and 3 negative pairs;
- excess replica-seconds: -90.

##### Mechanism and boundary

Premature forecast termination scaled down during real demand, while extended termination held capacity after demand declined. Equal absolute decision error became harm versus cost. Transition MAE distinguished the forecasts (0 versus 17.5 RPS), and safety was not tested.

#### Event presence

##### Tested

Missed versus false narrow spike, with MAE 6.0345 RPS and RMSE 14.5330 RPS in both conditions.

##### Observed magnitude

Missed minus false:

- desired-replica MAE: +0.3333;
- deficient replica-seconds: +180;
- request P99: +4805.43 ms, CI [4101.49, 5503.29];
- composite-SLO duration: +49.25 s, CI [43.375, 55.25];
- excess replica-seconds: -120.

##### Mechanism and boundary

The missed forecast withheld capacity during a real event; the false forecast supplied unused capacity for a nonexistent event. The direction persisted across all SLO definitions, capacity factors, repetitions, and leave-one-pair-out checks. Transition MAE also distinguished the pair.

#### Timing

##### Tested

Early versus late shifts under periodic and narrow-spike workloads, with equal MAE/RMSE within each workload.

##### Observed magnitude

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

##### Mechanism and boundary

Late spike prediction left less lead time than Pod readiness required. Periodic timing shifts were operationally diluted and produced the same capacity trajectories. Increasing horizon from 3 to 9 s reduced late-spike SLO duration by 16.2 s and Ready deficit by 216 RPS-s in the prospective robustness campaign.

#### Transition location

##### Tested

Equal-MAE/RMSE error during a stable versus transition period of a gradual ramp.

##### Observed magnitude

Transition minus stable:

- transition MAE: +1.6 RPS;
- desired-replica MAE: +0.0229;
- deficient replica-seconds: 0;
- excess replica-seconds: +11;
- P99: -1.17 ms, CI [-2.98, 0.26];
- SLO duration: -1.625 s, CI [-5.75, 2.0].

##### Mechanism and boundary

The altered transition decisions remained on the overprovisioning side, so the effect became small resource cost rather than harm. Transition placement was not inherently harmful.

#### Shape

##### Tested

Sharpened versus smoothed periodic-triangle forecasts with equal MAE, RMSE, and transition MAE.

##### Observed magnitude

- desired-replica MAE, deficiency, and excess: all exactly zero in both conditions;
- P99 difference: -0.42 ms, CI [-2.05, 0.81];
- SLO difference: +0.5 s, CI [-2.5, 3.75].

##### Mechanism and boundary

Both shapes remained inside the same replica-decision regions. Visual forecast shape did not matter without a threshold or readiness consequence.

#### Safety-net effect across the primary structures

Direct causal safety evidence exists only for persistent negative bias and missed peaks:

- persistent bias: deficiency -96.7%, P99 -32.2%, SLO -34.8% on average, +17 oracle-relative excess replica-seconds;
- missed peak: deficiency -88.3%, P99 -48.1%, SLO -75%, +15 oracle-relative excess replica-seconds.

Safety was not directly tested for duration, timing, location, shape, false peaks, or overprediction. It must be reported as not tested for those structures.

#### Reliability of the primary findings

##### Strongest controlled practical findings

- missed versus false harm/cost asymmetry;
- shortened versus extended harm/cost exchange;
- persistent negative versus positive decision-boundary effect;
- late narrow-spike harm;
- safety protection for missed peaks and deficiency under persistent bias.

##### Multiplicity-qualified findings

Most primary raw p-values were small, but no individual primary mutation outcome crossed 0.05 after Holm adjustment within the prespecified domain families. Decision and cost effects commonly reached 0.0546875. This is not proof of no effect; it reflects seven contrasts across multiple outcome families with eight pairs each.

##### Adjusted inferential finding

The narrow-spike-versus-periodic P99 timing interaction survived Holm correction at 0.0234375.

##### Negative findings

- shape did not affect controller or operational outcomes;
- periodic timing did not affect capacity summaries and barely affected P99;
- transition placement created only modest excess cost and no harm;
- positive persistent bias did not create oracle-relative excess;
- persistent-bias safety SLO improvement was heterogeneous;
- capacity calibration did not change controller behavior for a fully missed peak;
- transient-versus-persistent was not identified by an accuracy-matched randomized contrast.

#### Central hypothesis disposition

The central hypothesis is supported with qualification. Equal aggregate MAE/RMSE can conceal operationally important differences caused by direction, event presence, duration, and readiness-relative timing. However, not every structural difference matters: shape and periodic timing can be operationally equivalent when controller thresholds and readiness trajectories are unchanged. More context-sensitive metrics help, but no single forecast metric uniquely determines reliability and cost.

#### Final bounded primary-RQ answer

Within the tested system, error direction, duration, event presence, and timing changed Kubernetes outcomes by changing which replica boundary was crossed, whether decision error represented under- or overprovisioning, and whether requested replicas were Ready at the critical workload event. Shape and transition placement had limited or cost-only effects when they did not create a capacity shortage. Consequently, equal MAE/RMSE does not imply equal autoscaling quality, but structural error differences matter only through the controller and workload mechanisms they activate.


---

# Part III - Traceability, Reproducibility, and Completion

## Claim traceability

The companion `CLAIM-EVIDENCE-MATRIX.csv` contains eleven final claims. Each row records the evidence class, primary source, contrast or analysis, numerical support, uncertainty/test, scope, and support status. The matrix prevents a controlled causal claim from being silently replaced by a ranking correlation or an untested extrapolation.

## Source artifacts

The synthesis depends on these validated source classes:

- Step 15 immutable primary-run evidence and frozen experimental protocol;
- Step 16 safety controller, intervention logs, ablation dataset, and detailed report;
- Step 17 aligned timeline, run-level table, event-level table, processing contract, and data dictionary;
- Step 18 paired comparisons, interactions, descriptives, individual points, rankings, figures, protocol, and validation;
- Step 19 offline sensitivity tables, 40-run prospective campaign, attempt audit, final robustness report, and validation.

## Reproducibility

- `tools/build_detailed_report.py` rebuilds this report from the concise final document and nine evidence-ledger files.
- `tools/validate_step20.py` validates upstream source status, required files, claim count, selected numerical traces, required sections, multiplicity language, negative findings, and causal scope.
- `validation/step20-validation.json` records all checks.
- `validation/checksums.sha256` seals every Step 20 deliverable except the checksum file itself.

Step 20 changes no raw evidence and defines no new outcome. Every number is transcribed from a sealed analysis output or clearly labeled descriptive operational accounting.

## Completion-criteria assessment

| Criterion | Result |
|---|---|
| Every research question answered | Met |
| Every claim tied to evidence | Met through eleven-row claim matrix and nine ledgers |
| Controlled evidence separated from association | Met |
| Mechanisms tied to controller/readiness observations | Met |
| Workload context stated | Met |
| Safety effect and untested safety scope stated | Met |
| Negative and non-significant findings retained | Met |
| Equal-action cases retained | Met |
| Cases where conventional metrics were useful retained | Met |
| Multiple-comparison limitation retained | Met |
| Robustness and validity boundaries stated | Met |
| No claim exceeds tested system scope | Met |
| Reproducible validation provided | Met |

## Final completion statement

Step 20 establishes the final contribution without claiming universality. Within the tested autoscaling system, equal aggregate forecast accuracy can conceal different decisions, readiness timing, reliability harm, and resource cost. Those differences arise when error structure changes a replica threshold, the direction of capacity error, or the lead time available for Pods to become Ready. When structure does not change those mechanisms, different-looking forecasts can be operationally equivalent. The fixed safety layer corrects much of tested underprediction harm but leaves detection/readiness residuals and incurs a measurable capacity premium.
