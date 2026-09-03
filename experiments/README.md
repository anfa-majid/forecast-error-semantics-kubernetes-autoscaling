# Experiment packages

`protocol/` is the frozen design and randomized matrix. `primary/` contains the
safety-disabled campaign manager, immutable state ledger, validators, and
parameterized cloud runner. `safety/` contains the secondary ablation matrix and
runner. `capacity-profiling/` and `readiness-profiling/` document how the
empirical capacity lookup and six-second horizon were established.

The portable one-run demonstration is `scripts/run-example.ps1`. Direct study
replication requires a dedicated three-node K3s cluster and operator-supplied
addresses, SSH identity, kubeconfig, and container images.
