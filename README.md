# Forecast-Error Semantics in Predictive Kubernetes Autoscaling

This repository is the reproducibility artifact for the empirical study
*When Equal Forecast Error Is Not Operationally Equal: A Controlled Study of
Predictive Kubernetes Autoscaling*.

The study asks why workload forecasts with similar MAE and RMSE can produce
different Kubernetes scaling decisions, readiness trajectories, SLO outcomes,
and replica-time costs. The artifact contains the benchmark application,
predictive and reactive controller code, workload and forecast traces, frozen
experiment matrices, monitoring and processing tools, the analysis-ready
dataset, statistical programs, and reference results.

## Reproducibility levels

| Level | Requirement | What it verifies |
|---|---|---|
| A: analysis | Python only | Recreates the statistical tables and all six analysis figures from 142 accepted runs. |
| B: deterministic inputs | Python plus Pillow | Regenerates workloads, oracle decisions, forecast mutations, and accuracy-matched pairs. |
| C: controller | Go or Docker | Runs the Go unit tests and builds the benchmark and controller images. |
| D: example experiment | Docker, kind, kubectl, Helm, and PowerShell | Deploys the system and executes one workload/forecast replay. |
| E: full campaign | A dedicated three-node K3s environment | Repeats the frozen primary and safety experiment matrices. |

Levels A--C are offline. Levels D--E change a Kubernetes cluster and require
the operator to review the target context before proceeding.

## Quick reproduction of a paper figure

The included `data/processed/run-level.csv` contains one row for each of the
142 accepted runs. From the repository root on PowerShell 7:

```powershell
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
& .\scripts\reproduce-figures.ps1
```

On Linux or macOS, activate the virtual environment and run the three Python
programs shown in [docs/REPRODUCTION.md](docs/REPRODUCTION.md).

A successful run writes six SVG figures and the reconstructed statistical
tables to `results/reproduced/step18/`, validates their structure, and compares
their SHA-256 digests with `results/reference/statistical/`. The expected result
is `12/12 byte-identical reference artifacts`.

## Repository map

| Directory | Contents |
|---|---|
| `app/` | Go benchmark service, load checker, and pinned Docker build. |
| `controller/` | Fixed predictive autoscaler and integrated reactive safety net. |
| `safety-net/` | Independent Python reference implementation and observation transport. |
| `kubernetes/` | Benchmark, controller, local-cluster, and monitoring manifests. |
| `workloads/` | Five deterministic workload traces, request schedules, annotations, and generator. |
| `forecasts/oracle/` | Deterministic oracle decision policy and timelines. |
| `forecasts/mutations/` | Mutation catalog, generated candidates, metadata, and validator. |
| `forecasts/matched/` | Candidate grid, matching protocol, seven selected pairs, and rejection ledger. |
| `experiments/` | Capacity/readiness profiling, frozen protocol, primary runner, and safety runner. |
| `monitoring/` | Load generator, Kubernetes/Prometheus collectors, schemas, normalization, and plots. |
| `processing/` | Raw-to-analysis-ready processing and validation. |
| `analysis/` | Paired statistics, robustness logic, figure generation, and tests. |
| `data/` | Analysis-ready data and one representative commissioned run. |
| `results/` | Immutable reference outputs and locally reproduced outputs. |
| `docs/` | Setup, experiment, data, provenance, limitations, and release documentation. |
| `audit/` | Machine-readable and human-readable artifact verification records. |

## Recommended starting points

- Environment and installation: [docs/SETUP.md](docs/SETUP.md)
- Exact reproduction commands: [docs/REPRODUCTION.md](docs/REPRODUCTION.md)
- Kubernetes experiment workflow: [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md)
- Data dictionary and provenance: [docs/DATA.md](docs/DATA.md)
- Artifact limitations: [docs/LIMITATIONS.md](docs/LIMITATIONS.md)
- Release checklist: [docs/RELEASE-CHECKLIST.md](docs/RELEASE-CHECKLIST.md)
- Audited live-example evidence: [audit/LIVE-EXAMPLE-VALIDATION.md](audit/LIVE-EXAMPLE-VALIDATION.md)

## Scientific scope

The artifact reproduces the executed traces and controlled comparisons under
one fixed autoscaling policy. It does not compare forecasting algorithms,
estimate how frequently an error type occurs in production, or establish a
universal ordering of forecast errors. Requested replica-seconds are a resource
proxy, not direct monetary or energy cost. See `docs/study-synthesis/` for the
audited claim boundary.

## Citation and license

Machine-readable citation metadata is provided in [`CITATION.cff`](CITATION.cff).
Until the paper receives an archival citation, cite the artifact as:

> Anfa Majid. *Forecast-Error Semantics in Predictive Kubernetes Autoscaling:
> Reproducibility Artifact*, version 1.0.0, 2026.

Software, scripts, manifests, and configuration are licensed under the
[Apache License 2.0](LICENSE). Original data, traces, documentation, tables, and
figures are licensed under
[Creative Commons Attribution 4.0 International](LICENSE-DATA). The detailed
scope and third-party exception rule are in
[`licenses/README.md`](licenses/README.md).
