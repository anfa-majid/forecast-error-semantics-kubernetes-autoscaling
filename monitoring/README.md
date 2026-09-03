# ANFA Step 10 observability pipeline

Version `1.0.0` collects immutable raw evidence from the request scheduler, predictive controller, Kubernetes and Prometheus; normalizes it into a one-row-per-second causal timeline; validates coverage and timing; and generates dependency-free SVG plots.

Step 10 is complete and live-validated by `step10-pilot-20260809-150218`. `STEP10.md` is the canonical full research document; `STEP-10-DETAILED-REPORT.md` is the concise completion report. Run unit tests with:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m unittest discover -s tests -v
```

The local end-to-end commissioning entrypoint is `scripts/run-step10-local-pilot.ps1`. It uses the frozen narrow-spike trace, temporarily changes the benchmark ServiceMonitor from 15-second to one-second scraping, restores it in `finally`, uses unique immutable controller inputs, and marks the resulting run `commissioning_only`.
