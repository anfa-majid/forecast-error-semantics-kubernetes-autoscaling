# Source and packaging provenance

The artifact was assembled from the validated research archive without
re-running or altering accepted experiments.

| Artifact directory | Authoritative source version |
|---|---|
| `app/` | Step 4 benchmark application |
| `controller/` | Step 16 controller v1.1.2, including the reactive safety net |
| `workloads/` | Step 7 workload suite v1.0.0 |
| `forecasts/oracle/` | Step 8 oracle reference v1.0.0 |
| `forecasts/mutations/` | Step 11 mutation framework v1.0.0 |
| `forecasts/matched/` | Step 12 accuracy-matched dataset v1.0.0 |
| `experiments/protocol/` | Step 14 frozen protocol v1.0.0 |
| `experiments/primary/` | Step 15 primary campaign framework v1.0.0 |
| `experiments/safety/` | Step 16 safety-net ablation framework |
| `monitoring/` | Step 10 observability pipeline v1.0.0 |
| `processing/` and `data/processed/` | Step 17 analysis-ready dataset v1.0.0 |
| `analysis/` and `results/reference/statistical/` | Step 18 analysis v1.1.0 |
| `results/reference/robustness/` | Step 19 final robustness package |
| `docs/study-synthesis/` | Step 20 validated final synthesis |

Packaging changes are limited to directory normalization, portable wrappers,
removal of machine-specific default paths and host identifiers, documentation,
and repository-level integrity checks. Historical scientific identifiers in
data (for example policy IDs and run IDs) are retained so results remain
traceable to the sealed research archive.

The release audit will record source and packaged SHA-256 mappings for every
copied canonical file whose content was not intentionally adapted.
