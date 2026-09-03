# Step 20 Final Findings and Claims

## Primary deliverable

`FINAL-FINDINGS-AND-CLAIMS.md` answers the main, primary, and secondary research questions and records the final bounded claims.

`STEP-20-DETAILED-RESEARCH-REPORT.md` is the self-contained end-to-end report. It includes the research chain, evidence hierarchy, statistical interpretation rules, integrated findings, all nine detailed evidence appendices, traceability, reproducibility, and completion assessment.

## Traceability

- `CLAIM-EVIDENCE-MATRIX.csv` maps each final claim to its evidence class, source, effect, uncertainty, scope, and status.
- `evidence-ledger/` contains the detailed contrast-by-contrast audits used to construct the final document.
- `tools/validate_step20.py` checks source validation, required files, claim count, selected numerical values, required sections, multiplicity language, negative findings, and causal scope.
- `tools/build_detailed_report.py` deterministically rebuilds the detailed report from the audited concise report and evidence ledger.
- `validation/step20-validation.json` records the reproducible completion audit.
- `validation/checksums.sha256` seals the Step 20 package files.

Step 20 performs synthesis only. It does not alter raw evidence, rerun experiments, or redefine Step 17/18 metrics.
