from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("step6/runs")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("step6/report")
TREATMENT = sys.argv[3] if len(sys.argv) > 3 else "cached-main"


def percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile: conservative and reproducible for small samples."""
    ordered = sorted(values)
    return ordered[max(0, math.ceil(p / 100 * len(ordered)) - 1)]


def describe(values: list[float]) -> dict[str, float | int]:
    return {
        "n": len(values),
        "median": statistics.median(values),
        "p90": percentile(values, 90),
        "p95": percentile(values, 95),
        "maximum": max(values),
        "minimum": min(values),
    }


trials: list[dict] = []
pods: list[dict] = []
for summary_path in sorted(ROOT.glob("*/trial-summary.json")):
    trial = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    if (
        trial.get("valid") is not True
        or trial.get("cache_treatment") != TREATMENT
        or int(trial.get("repetition", 0)) < 1
    ):
        continue
    trial["directory"] = str(summary_path.parent)
    trials.append(trial)
    pod_path = summary_path.parent / "per-pod.csv"
    with pod_path.open(encoding="utf-8-sig", newline="") as handle:
        pods.extend(csv.DictReader(handle))

if not trials:
    raise SystemExit(f"No valid Step 6 trials found below {ROOT}")

groups: dict[tuple[str, int], list[dict]] = defaultdict(list)
for trial in trials:
    groups[(trial["cache_treatment"], int(trial["increment"]))].append(trial)

rows = []
for (cache, increment), items in sorted(groups.items()):
    trial_metrics = {
        "decision_delay_s": [float(x["decision_delay_ms"]) / 1000 for x in items],
        "deployment_api_delay_s": [float(x["scale_api_roundtrip_ms"]) / 1000 for x in items],
        "trial_readiness_delay_s": [float(x["trial_readiness_delay_s"]) for x in items],
        "trial_effective_serving_delay_s": [float(x["trial_effective_serving_delay_s"]) for x in items],
    }
    matching_pods = [p for p in pods if int(p["increment"]) == increment]
    for metric in ("creation_delay_s", "scheduling_delay_s", "startup_delay_s", "container_to_ready_s"):
        trial_metrics[f"per_pod_{metric}"] = [float(p[metric]) for p in matching_pods]
    for metric, values in trial_metrics.items():
        stats = describe(values)
        rows.append({"cache_treatment": cache, "increment": increment, "metric": metric, **stats})

OUT.mkdir(parents=True, exist_ok=True)
with (OUT / "delay-distributions.csv").open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
with (OUT / "all-trials.csv").open("w", encoding="utf-8", newline="") as handle:
    fields = sorted({k for row in trials for k in row})
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader(); writer.writerows(trials)
with (OUT / "all-pods.csv").open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(pods[0]))
    writer.writeheader(); writer.writerows(pods)

effective = [float(x["trial_effective_serving_delay_s"]) for x in trials]
p95 = percentile(effective, 95)
margin = max(2.0, 0.20 * p95)
horizon = math.ceil(p95 + margin)
result = {
    "schema_version": 1,
    "valid_trial_count": len(trials),
    "cache_treatment": TREATMENT,
    "valid_trials_by_increment": {str(i): sum(1 for x in trials if int(x["increment"]) == i) for i in (1, 2, 3)},
    "distribution_method": "nearest-rank",
    "overall_effective_serving_delay_seconds": describe(effective),
    "safety_margin_seconds": margin,
    "selected_local_forecast_horizon_seconds": horizon,
    "selection_rule": "ceil(P95 effective serving delay + max(2 seconds, 20% of P95))",
    "warning": "Local kind/Docker Desktop result; repeat on final native K3s environment.",
}
(OUT / "forecast-horizon-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
