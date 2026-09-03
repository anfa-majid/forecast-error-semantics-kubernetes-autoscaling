# Data documentation

## Included datasets

### `data/processed/aligned-timeline.csv`

One row per accepted run-second: 59,400 rows from 142 runs. It aligns workload,
forecast, desired replica, requested replica, Ready replica, request outcome,
latency, and capacity-accounting fields. This file supports mechanism and
time-series inspection but is not the inferential unit.

### `data/processed/run-level.csv`

One row per accepted run: 142 rows. This is the input to the paired statistical
analysis. The run is the inferential unit.

### `data/processed/event-level.csv`

One row per annotated workload event: 290 rows. This supports event-local
diagnostics and does not create independent experimental replicates.

### `data/example-run/`

A commissioned narrow-spike/oracle run containing inputs, metadata, controller
logs, Kubernetes snapshots, selected Prometheus exports, the normalized
timeline, plots, and validation records. Request-level JSONL is omitted from the
compact artifact; its aggregate summary and derived timeline are retained.

## Definitions

The authoritative column definitions, units, missingness rules, and formulas
are in `processing/DATA-DICTIONARY.md`. Important distinctions are:

- desired replicas are policy decisions;
- requested replicas are Deployment-scale commands;
- Ready replicas are observed usable Pods;
- deficient replica-seconds and excess replica-seconds compare requested
  occupancy with the oracle decision trajectory;
- Ready-capacity deficit uses the empirical capacity lookup;
- composite-SLO duration is the union of violating seconds and its component
  durations must not be summed;
- replica-seconds are a resource proxy, not money or energy.

## Provenance and exclusions

The processed data were deterministically created from 132 accepted primary
cells and 10 accepted safety-on cells. Across the full execution audit there
were 173 attempts: 142 accepted, 30 technically invalid, and one aborted. No
attempt was excluded because its outcome was unfavorable.

The complete raw archive remains external because it is several gigabytes.
Publication must provide its immutable archive location and SHA-256 digest in
this document. Until then, the repository supports exact analysis reproduction
and schema-level inspection, but not independent reprocessing of all raw runs.

## Integrity

`data/processed/checksums.sha256` records the authoritative Step 17 checksums.
The repository-level checksum manifest generated during release covers every
tracked artifact file except the checksum manifest itself and generated output.
