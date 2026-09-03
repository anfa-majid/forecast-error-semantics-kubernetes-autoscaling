# Kubernetes experiment workflow

## Safety warning

The experiment runner scales a Deployment, creates ConfigMaps, opens local port
forwards, and generates load. Use a disposable research cluster. Confirm the
active context before every live run; do not point the scripts at a production
cluster.

## Study architecture

The measured system consists of one benchmark Deployment, a single-writer
predictive autoscaler, an optional overload-based reactive floor, a deterministic
request scheduler, Kubernetes state collection, and Prometheus export. The
controller maps the forecast at `t + 6 s` through the empirical capacity table
`1->30`, `2->40`, `3->55`, and `4->65 RPS`, with one-second decisions and a
30-second predictive scale-down stabilization window.

## Local functional example

1. Start Docker.
2. Review the current Kubernetes context.
3. Create the disposable kind cluster and build/import images:

   ```powershell
   & .\scripts\setup-kind.ps1
   ```

4. Run the narrow-spike oracle example:

   ```powershell
   & .\scripts\run-example.ps1
   ```

5. Inspect the new directory under `results/reproduced/example-run/`.

The local example verifies deployment, forecast replay, scaling commands, Pod
readiness observation, request scheduling, and evidence collection. It does not
claim to reproduce the Azure/K3s latency distribution. A successful run writes
`example-run-validation.json` with `valid: true`; validation requires the exact
5,550-request schedule, 180 forecast-aligned controller decisions, successful
scale API updates, contiguous Kubernetes evidence, and a complete 180-row
normalized timeline.

The runner retains the complete controller text stream in
`raw/controller-complete.log` and writes only JSON decision records to
`raw/controller.jsonl`. If an already completed run was interrupted only during
post-processing, `scripts/finalize-example.ps1` can retrieve the current
controller log, normalize the retained evidence, and apply the same validator.

The example uses `kubectl port-forward` for safe local access. A port-forward
may remain attached to one backend, so request latency from this demonstration
must not be interpreted as a multi-Pod capacity or load-balancing measurement.

## Direct replication of the study environment

Provision three amd64 Ubuntu 24.04.4 nodes and install K3s
`v1.36.1+k3s1`/containerd `2.2.3-k3s1`. Apply the benchmark and monitoring
manifests, run the capacity and readiness profiling procedures, and confirm that
the capacity lookup and forecast horizon remain valid before executing the
frozen matrix.

The primary protocol is in `experiments/protocol/`; primary and safety runners
are in `experiments/primary/` and `experiments/safety/`. Their cloud entrypoints
require explicit server, worker, SSH-user, key, kubeconfig, Python, and output
parameters. The original public IP, account name, drive path, and private
kubeconfig path are deliberately not distributed.

## Required run evidence

Every accepted run must retain:

- exact workload, request schedule, forecast, oracle, policy, and protocol;
- immutable run and condition identifiers;
- controller JSONL;
- request-level or losslessly summarized load-generator evidence;
- Kubernetes state and events;
- Prometheus exports;
- pre/post clock attestations;
- rendered manifests and image digests;
- normalization, validation, and SHA-256 records.

Failed and superseded attempts must remain append-only and must not be
overwritten. Outcome values are not valid exclusion criteria.
