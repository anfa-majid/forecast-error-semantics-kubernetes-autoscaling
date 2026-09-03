# Reproduction procedures

All commands are run from the repository root unless stated otherwise.

## A. Recreate the statistical results and figures

PowerShell:

```powershell
& .\scripts\reproduce-figures.ps1
```

Portable Python equivalent:

```bash
python analysis/tools/analyze_step18.py \
  --run-level data/processed/run-level.csv \
  --output-directory results/reproduced/step18/output

python analysis/tools/create_step18_figures.py \
  --analysis-directory results/reproduced/step18/output \
  --output-directory results/reproduced/step18/figures

python analysis/tools/validate_step18.py \
  --dataset-directory results/reproduced/step18/output \
  --figures-directory results/reproduced/step18/figures
```

Expected validation invariants:

- 142 run-level rows;
- 112 primary runs and 10 safety-on runs within the 142-run dataset;
- 56 primary and 16 safety tests;
- 16 interaction contrasts and 28 ranking pairs;
- six well-formed SVG figures;
- the 12 core tables/figures are byte-identical to the reference outputs.

## B. Verify deterministic input packages

```powershell
& .\scripts\verify-deterministic-inputs.ps1
```

This runs the workload, oracle, mutation, and matching validators. The mutation
and matching validators regenerate their products in temporary directories and
compare them byte-for-byte with the packaged versions.

## C. Run the offline test suite

```powershell
& .\scripts\run-offline-tests.ps1
```

This includes the Python unit tests, data validators, analysis reconstruction,
and Go tests when Go is available. A missing Go executable is reported as a
skipped optional check; it is not silently treated as a pass.

For the repository-wide packaging audit, first generate the immutable release
manifest and then run the verifier:

```powershell
& .\scripts\generate-checksums.ps1
& .\scripts\verify-artifact.ps1 -RunOfflineTests
```

The repository-level manifest uses SHA-256 over canonical LF bytes for valid
UTF-8 text and over the original bytes for binary files. This definition makes
the release seal invariant to Git's CRLF/LF checkout behavior while retaining
byte-exact verification for binary evidence.

Use `-RequireGo` for final release certification on a machine with Go 1.24.6.

## D. Reprocess raw campaign evidence

The complete 142-run raw archive is too large for the compact Git repository.
If it is downloaded separately and arranged as documented in the processing
data dictionary, run:

```powershell
python processing/tools/process_step17.py `
  --research-root <raw-archive-root> `
  --output-directory results/reproduced/step17

python processing/tools/validate_step17.py `
  --dataset-directory results/reproduced/step17
```

The included `data/example-run/` demonstrates the raw-run schema. The included
analysis-ready dataset allows Levels A--C without downloading the multi-gigabyte
raw campaign.

## E. Run a live example

Read [EXPERIMENTS.md](EXPERIMENTS.md), verify the target Kubernetes context,
then use the local kind setup and example runner. Live runs are expected to
vary in latency and readiness because hardware and cluster scheduling differ;
functional equivalence is not statistical replication. Success is determined
by `example-run-validation.json`, not merely by process completion. The audited
packaging run is documented in
[`../audit/LIVE-EXAMPLE-VALIDATION.md`](../audit/LIVE-EXAMPLE-VALIDATION.md).
