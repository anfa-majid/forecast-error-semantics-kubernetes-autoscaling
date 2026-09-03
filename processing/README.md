# Step 17 — Analysis-Ready Dataset

This package deterministically processes the 132 accepted Step 15 runs and 10 accepted Step 16 runs into:

- `output-final/aligned-timeline.csv` — 59,400 one-second rows;
- `output-final/run-level.csv` — 142 run summaries;
- `output-final/event-level.csv` — 290 workload events;
- `DATA-DICTIONARY.md` — alignment, formulas, missingness, and columns;
- `output-final/step17-validation.json` — automated and manual checks.

Raw evidence is never modified. Reproduce with:

```powershell
python tools/process_step17.py --research-root <code-directory> --output-directory output-final
python tools/validate_step17.py --dataset-directory output-final
```

Important limitation: Step 16 remote Kubernetes snapshots contain collector errors because remote `kubectl` was unavailable. Step 16 Ready replicas come from the controller's live Deployment reads; Step 16 Pod-event fields remain missing and explicitly labeled.
