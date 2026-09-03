# Step 16 Reactive Safety-Net Ablation

Status: safety contract, reference engine, observed-demand transport, controller v1.1 single-writer arbitration, Kubernetes manifests, safety-specific run validator, campaign manager, and cloud runner implemented. The 21-test offline suite passes. The Go/container build passed and the identical image was imported on all three Azure nodes; final cluster preflight remains before run 1.

Commissioned controller artifact: `anfa/predictive-autoscaler:1.1.0@sha256:360c05c6e36f52ff1672e35378bc3c992fcf2616f24b4285e828d96cd7f47164`; exported archive SHA-256 `df482ec962a242d49c391bb566a962f52c9d8bb6c9bd46aeea630ba4335edbbd`.

The frozen scope is the ten `secondary_safety` cells from Step 14: five persistent-negative-bias repetitions and five missed-peak repetitions. Safety-off comparators are the corresponding accepted Step 15 runs.

The safety rule evaluates completed one-second load-generator dispatch windows. After two consecutive windows where observed demand exceeds empirically validated Ready capacity, it raises a safety floor to the current-demand requirement. The sole scale writer arbitrates `max(predictive command, safety floor)`. The floor remains active while observed demand requires more replicas than the predictive command, then releases after 30 consecutive seconds without that protection need. Missing observations are logged without intervention; demand above 65 RPS invalidates the run.

Run offline tests with `python -m unittest discover -s tests -v`.

Before cloud execution, build and distribute the controller v1.1 image, then stage the augmented collector with `scripts/prepare-step16-loadgen.ps1`. Runs are accepted only after the independent validator matches every observation and safety decision against the frozen rule.
