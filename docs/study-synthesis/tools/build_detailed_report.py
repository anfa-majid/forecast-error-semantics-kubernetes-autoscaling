from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
FINAL=ROOT/"FINAL-FINDINGS-AND-CLAIMS.md"
LEDGER=ROOT/"evidence-ledger"
OUT=ROOT/"STEP-20-DETAILED-RESEARCH-REPORT.md"

ledger_files=[
  "01-error-direction.md",
  "02-error-duration.md",
  "03-event-presence.md",
  "04-error-timing.md",
  "05-error-placement.md",
  "06-error-shape.md",
  "07-reactive-safety-net.md",
  "08-metric-usefulness-and-rankings.md",
  "09-main-and-primary-rq-answers.md",
]

front="""# Step 20 - Detailed End-to-End Research Report

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

"""

tail="""

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
"""

parts=[front,FINAL.read_text(encoding="utf-8").replace("# Step 20 - Final Findings and Claims\n","",1),"\n\n---\n\n# Part II - Detailed Evidence Ledger\n"]
for i,name in enumerate(ledger_files,1):
    content=(LEDGER/name).read_text(encoding="utf-8")
    parts.append(f"\n\n---\n\n## Appendix {i} - {name[:-3].replace('-', ' ').title()}\n\n")
    # Demote original headings so the combined report has one coherent hierarchy.
    for line in content.splitlines():
        if line.startswith("#"):line="##"+line
        parts.append(line+"\n")
parts.append(tail)
OUT.write_text("".join(parts),encoding="utf-8")
print(json.dumps({"output":str(OUT),"bytes":OUT.stat().st_size,"appendices":len(ledger_files)}))

