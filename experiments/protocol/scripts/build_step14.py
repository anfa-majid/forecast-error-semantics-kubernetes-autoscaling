from __future__ import annotations

import csv
import hashlib
import json
import random
import shutil
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "step-14-final-experimental-protocol-v1.0.0"
S7 = ROOT / "outputs" / "step-7-workload-suite-v1.0.0"
S8 = ROOT / "outputs" / "step-8-oracle-reference-v1.0.0"
S9 = ROOT / "outputs" / "step-9-predictive-autoscaler-v1.0.0"
S12 = ROOT / "outputs" / "step-12-accuracy-matched-forecasts-v1.0.0"
S13 = ROOT / "outputs" / "step-13-pilot-experiments-v1.0.0"

VERSION = "1.0.0"
SEED = 14001
WORKLOAD_SECONDS = {
    "gradual-ramp-v1": 480,
    "narrow-spike-v1": 180,
    "sustained-peak-v1": 360,
    "periodic-triangle-v1": 720,
}
PAIR_CODES = {
    "pair-01-direction_bias": "p01",
    "pair-02-duration": "p02",
    "pair-03-event_presence": "p03",
    "pair-04-location": "p04",
    "pair-05-shape": "p05",
    "pair-06-timing_periodic": "p06",
    "pair-07-timing_spike": "p07",
}
SAFETY_SECONDARY = {
    ("pair-01-direction_bias", "a"),  # persistent negative bias
    ("pair-03-event_presence", "b"),  # missed peak
}


def dump_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_pairs() -> list[dict]:
    pairs = []
    for path in sorted((S12 / "accepted-pairs").glob("*/pair-metadata.json")):
        pairs.append(json.loads(path.read_text(encoding="utf-8")))
    assert len(pairs) == 7
    return pairs


def forecast_ref(pair: dict, side: str) -> tuple[str, str, str, str]:
    key = "forecast_a" if side == "a" else "forecast_b"
    item = pair[key]
    accepted = S12 / "accepted-pairs" / pair["pair_id"] / f"forecast-{side}.csv"
    assert accepted.exists()
    return item["candidate_id"], item["semantic"], str(accepted.relative_to(ROOT)).replace("\\", "/"), sha256(accepted)


def run_row(pair: dict | None, side: str, rep: int, safety: bool, phase: str, workload: str | None = None) -> dict:
    if pair is None:
        assert workload
        code = {"gradual-ramp-v1": "ramp", "narrow-spike-v1": "spike", "sustained-peak-v1": "sustain", "periodic-triangle-v1": "periodic"}[workload]
        condition_id = f"oracle-{code}"
        forecast_id = f"{workload}__oracle"
        semantic = "oracle"
        source = S9 / "testdata" / "forecasts" / f"{workload}.oracle-forecast.csv"
        pair_id = "reference-oracle"
        side_name = "reference"
    else:
        workload = pair["trace_id"]
        pair_id = pair["pair_id"]
        condition_id = f"{PAIR_CODES[pair_id]}-{side}"
        forecast_id, semantic, source_rel, source_hash = forecast_ref(pair, side)
        source = ROOT / source_rel
        side_name = side
    suffix = "s1" if safety else "s0"
    run_id = f"final-{condition_id}-r{rep:02d}-{suffix}"
    collection_s = WORKLOAD_SECONDS[workload] + 30 + 90
    planned_wall_s = collection_s + 120 + 30
    workload_file = S7 / "request-schedules" / f"{workload}.requests.csv"
    oracle_file = S8 / "timelines" / f"{workload}.oracle-decisions.csv"
    return {
        "run_id": run_id,
        "phase": phase,
        "pair_id": pair_id,
        "condition_side": side_name,
        "forecast_condition": semantic,
        "forecast_id": forecast_id,
        "workload_id": workload,
        "repetition": rep,
        "safety_enabled": str(safety).lower(),
        "workload_duration_s": WORKLOAD_SECONDS[workload],
        "collection_duration_s": collection_s,
        "planned_wall_duration_s": planned_wall_s,
        "workload_path": str(workload_file.relative_to(ROOT)).replace("\\", "/"),
        "workload_sha256": sha256(workload_file),
        "forecast_path": str(source.relative_to(ROOT)).replace("\\", "/"),
        "forecast_sha256": source_hash if pair is not None else sha256(source),
        "oracle_path": str(oracle_file.relative_to(ROOT)).replace("\\", "/"),
        "oracle_sha256": sha256(oracle_file),
        "status": "planned",
        "attempt": 1,
    }


def make_rows(pairs: list[dict]) -> list[dict]:
    rows = []
    for rep in range(1, 9):
        for pair in pairs:
            for side in ("a", "b"):
                rows.append(run_row(pair, side, rep, False, "primary"))
    for rep in range(1, 6):
        for workload in WORKLOAD_SECONDS:
            rows.append(run_row(None, "reference", rep, False, "reference", workload))
    pair_map = {p["pair_id"]: p for p in pairs}
    for rep in range(1, 6):
        for pair_id, side in sorted(SAFETY_SECONDARY):
            rows.append(run_row(pair_map[pair_id], side, rep, True, "secondary_safety"))
    return rows


def randomized_order(rows: list[dict]) -> list[dict]:
    rng = random.Random(SEED)
    ordered = []
    # Eight balanced blocks. Blocks 1-5 also contain all references and the two safety runs.
    for block in range(1, 9):
        candidates = [r for r in rows if r["phase"] == "primary" and r["repetition"] == block]
        if block <= 5:
            candidates += [r for r in rows if r["phase"] != "primary" and r["repetition"] == block]
        best = None
        for _ in range(500):
            trial = candidates[:]
            rng.shuffle(trial)
            bad = sum(trial[i]["forecast_condition"] == trial[i-1]["forecast_condition"] and trial[i]["workload_id"] == trial[i-1]["workload_id"] for i in range(1, len(trial)))
            if best is None or bad < best[0]:
                best = (bad, trial)
            if bad == 0:
                break
        for row in best[1]:
            copy = dict(row)
            copy["randomization_block"] = block
            copy["sequence"] = len(ordered) + 1
            ordered.append(copy)
    return ordered


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    for name in ("configuration", "matrix", "analysis", "validation", "manifests", "scripts"):
        (OUT / name).mkdir(parents=True, exist_ok=True)
    pairs = load_pairs()
    rows = make_rows(pairs)
    ordered = randomized_order(rows)

    conditions = []
    for pair in pairs:
        for side in ("a", "b"):
            fid, semantic, path, digest = forecast_ref(pair, side)
            conditions.append({
                "pair_id": pair["pair_id"], "contrast_group": pair["contrast_group"], "workload_id": pair["trace_id"],
                "side": side, "semantic": semantic, "forecast_id": fid, "forecast_path": path, "forecast_sha256": digest,
                "mae_rps": pair[f"forecast_{side}"]["metrics"]["mae_rps"],
                "rmse_rps": pair[f"forecast_{side}"]["metrics"]["rmse_rps"],
                "signed_bias_rps": pair[f"forecast_{side}"]["metrics"]["signed_bias_rps"],
                "primary_repetitions": 8,
                "safety_enabled_repetitions": 5 if (pair["pair_id"], side) in SAFETY_SECONDARY else 0,
            })
    write_csv(OUT / "matrix" / "condition-catalog.csv", conditions)
    write_csv(OUT / "matrix" / "run-matrix.csv", rows)
    write_csv(OUT / "matrix" / "randomized-run-order.csv", ordered)
    dump_json(OUT / "matrix" / "run-matrix.json", {"schema_version": VERSION, "seed": SEED, "runs": ordered})

    protocol = {
        "schema_version": VERSION,
        "protocol_id": "anfa-final-experimental-protocol-v1",
        "status": "frozen-before-final-outcomes",
        "frozen_utc": "2026-08-12T17:57:02.5346136Z",
        "randomization": {"seed": SEED, "method": "eight deterministic balanced blocks; Python random.Random MT19937; no identical workload-condition adjacency when achievable"},
        "matrix": {"primary_matched_runs": 112, "oracle_reference_runs": 20, "secondary_safety_runs": 10, "total_runs": 142},
        "repetitions": {"primary_each_condition": 8, "oracle_each_workload": 5, "secondary_safety_each_selected_condition": 5},
        "safety": {"primary": False, "secondary_selected": True, "selected": ["persistent_negative_bias on sustained-peak-v1", "missed_peak on narrow-spike-v1"]},
        "matching_tolerances": {"mae_relative_difference_lt": 0.02, "rmse_relative_difference_lt": 0.03, "source": "Step 12 frozen protocol"},
        "slo": {"p99_latency_ms_lte": 300, "failure_rate_lt": 0.01, "completion_ratio_gte": 0.99},
        "fixed_system": {
            "controller_version": "1.0.0",
            "controller_policy_id": "anfa-empirical-replica-policy-v1",
            "controller_policy_sha256": "86f4add7a80b9288abc82d42e3a1b55ad670b4da9a6a942ba302674ab513193b",
            "capacity_lookup_rps": {"1": 30.0, "2": 40.0, "3": 55.0, "4": 65.0},
            "min_replicas": 1, "max_replicas": 4, "initial_replicas": 1,
            "safety_factor": 1.0, "forecast_horizon_s": 6, "decision_interval_s": 1,
            "scale_down_stabilization_s": 30, "max_scale_down_step": 1,
            "max_scale_up_step": 0,
            "application_image": "anfa-step6-registry:5000/anfa/benchmark-app@sha256:3e918e5a462fbbb61bf988366e7e05f33e6987af5741c2283cf9f9d9a34a6e73",
            "cluster": {
                "kubernetes_version": "v1.36.1+k3s1", "container_runtime": "containerd://2.2.3-k3s1",
                "os_image": "Ubuntu 24.04.4 LTS", "architecture": "amd64",
                "nodes": ["anfa-server", "anfa-worker1", "anfa-worker2"],
                "roles": {"anfa-server": "control-plane/infrastructure", "anfa-worker1": "experiment-worker", "anfa-worker2": "experiment-worker"}
            },
            "pre_run_s": 30, "post_run_s": 90, "t0_lead_s": 120,
            "inter_run_stable_s": 30, "maximum_clock_skew_ms": 100,
            "maximum_dispatch_lateness_ms": 100,
            "kubernetes_coverage_gte": 0.95, "maximum_missing_consecutive_s": 1
        },
        "primary_outcome": "deficient_ready_replica_seconds_vs_oracle",
        "secondary_outcomes": ["excess_ready_replica_seconds_vs_oracle", "slo_violation_seconds", "p99_latency_ms", "failure_rate", "completion_ratio", "scale_up_lateness_s"],
        "analysis": {
            "unit": "run",
            "primary_estimand": "within-block median paired difference, side B minus side A, for each of seven matched pairs",
            "test": "two-sided exact paired permutation test where feasible; Wilcoxon signed-rank sensitivity analysis",
            "interval": "95% bootstrap confidence interval for paired median difference using fixed analysis seed 14002",
            "multiplicity": "Holm family-wise correction across seven pair-specific tests for the primary outcome; secondary outcomes reported with unadjusted exploratory intervals and clearly labelled",
            "alpha": 0.05,
            "missing": "no outcome imputation; technical invalid attempts are replaced using the same preassigned run cell and attempt increment",
        },
        "invalid_if": [
            "preflight or reset fails", "clock skew exceeds 100 ms", "dispatch lateness exceeds 100 ms",
            "controller input identity differs from metadata", "controller decisions are incomplete or disagree with independent replay",
            "load generator exits nonzero or terminal request accounting is below 99 percent",
            "Kubernetes snapshot coverage is below 95 percent or more than one consecutive second is missing",
            "required Prometheus, Kubernetes, controller, workload, forecast, metadata, or checksum evidence is missing",
            "another scaler targets benchmark-app", "manual intervention changes replicas during collection",
            "frozen workload, forecast, controller, application image, cluster topology, or protocol hash is not the declared version",
        ],
        "never_exclude_for": ["high latency", "SLO violation", "request failure caused by capacity", "slow readiness", "underprovisioning", "overprovisioning", "unexpected or unfavorable outcome"],
        "failed_run_handling": "Preserve the failed attempt and evidence; record a reason code; rerun the same matrix cell with attempt incremented. Do not substitute another condition or inspect outcomes to decide replacement.",
        "scope_exclusions": {"ordinary_baseline_forecast": "not included because no separately frozen ordinary baseline exists", "reactive_hpa": "not included because predictive-versus-reactive performance is not a central research question", "stable_noisy_control": "not included in the main matrix because none of the seven Step 12 matched pairs use it"},
    }
    dump_json(OUT / "configuration" / "frozen-protocol.json", protocol)

    by_phase = Counter(r["phase"] for r in rows)
    by_workload = Counter(r["workload_id"] for r in rows)
    pure_collection = sum(int(r["collection_duration_s"]) for r in rows)
    planned_wall = sum(int(r["planned_wall_duration_s"]) for r in rows)
    runtime_rows = [{"category": "total", "runs": len(rows), "collection_hours": round(pure_collection/3600, 3), "planned_wall_hours": round(planned_wall/3600, 3)}]
    for key in sorted(by_workload):
        subset = [r for r in rows if r["workload_id"] == key]
        runtime_rows.append({"category": key, "runs": len(subset), "collection_hours": round(sum(int(r["collection_duration_s"]) for r in subset)/3600, 3), "planned_wall_hours": round(sum(int(r["planned_wall_duration_s"]) for r in subset)/3600, 3)})
    write_csv(OUT / "analysis" / "runtime-estimate.csv", runtime_rows)

    report = f"""# Step 14 — Frozen Final Experimental Protocol and Run Matrix

Version: {VERSION}  
Protocol ID: `anfa-final-experimental-protocol-v1`  
Status: **frozen before final operational outcomes**

## Completion statement

Step 14 converts the verified artifacts from Steps 7–13 into a deterministic, outcome-blind execution and analysis plan. The package contains {len(rows)} uniquely identified runs: {by_phase['primary']} primary matched-error runs, {by_phase['reference']} oracle reference runs, and {by_phase['secondary_safety']} selected secondary safety-enabled runs.

## Research design

Seven Step 12 pairs are retained because each passed the preregistered MAE (<2%) and RMSE (<3%) matching tolerances, semantic gates, byte-exact regeneration, and outcome-blind validation. Each pair is evaluated only on its scientifically applicable workload. The primary controller safety net is disabled. Eight repetitions are assigned to each of the 14 matched forecast conditions. Oracle references receive five repetitions on each of the four workloads. The secondary safety analysis repeats persistent negative bias and missed peak five times with safety enabled.

The ordinary baseline forecast, reactive HPA, and stable/noisy control are excluded for explicit scope reasons recorded in the machine-readable protocol. Their exclusion is not based on Kubernetes outcomes.

## Final counts

| Component | Calculation | Runs |
|---|---:|---:|
| Primary matched comparisons | 7 pairs × 2 sides × 8 repetitions | 112 |
| Oracle references | 4 workloads × 5 repetitions | 20 |
| Secondary safety analysis | 2 critical conditions × 5 repetitions | 10 |
| **Total** | | **142** |

## Workload applicability

| Workload | Matched questions |
|---|---|
| gradual-ramp-v1 | stable-period versus transition-period error |
| narrow-spike-v1 | missed versus false peak; early versus late timing |
| sustained-peak-v1 | negative versus positive persistent bias; shortened versus extended peak |
| periodic-triangle-v1 | smoothed versus sharpened shape; early versus late timing |

## Randomization

The order is generated with seed `{SEED}` in eight balanced repetition blocks. Blocks 1–5 contain matched conditions, four distributed oracle references, and two secondary safety runs. Blocks 6–8 contain matched conditions. Forecast sides are shuffled within every block, and identical workload/condition adjacency is avoided when possible. The generated sequence is immutable; deviations must be recorded, not silently reordered.

## Outcomes and analysis

The primary outcome is deficient ready-replica-seconds relative to the oracle. Secondary outcomes are excess ready-replica-seconds, SLO-violation seconds, P99 latency, failure rate, completion ratio, and scale-up lateness. Pair-specific effects are computed as side B minus side A within repetition block. The primary inference uses a two-sided exact paired permutation test where feasible, with a Wilcoxon signed-rank sensitivity analysis and a 95% bootstrap interval for the paired median. Holm correction controls the family-wise error rate across the seven primary pair tests.

The SLO remains frozen from Step 13: P99 ≤ 300 ms, failure rate <1%, and completion ratio ≥99%.

## Failed runs and exclusions

Only technical invalidity can exclude an attempt. High latency, SLO failure, capacity shortage, readiness delay, overprovisioning, and unexpected outcomes remain valid evidence. Every invalid attempt is retained with its reason. Its predefined matrix cell is rerun with an incremented attempt number; no outcome-based substitution is permitted.

## Runtime

Scheduled collection time is approximately {pure_collection/3600:.2f} hours. Including the frozen T0 lead and inter-run stability allowance, planned cluster occupancy is approximately {planned_wall/3600:.2f} hours before contingencies. A 15% operational contingency gives approximately {planned_wall/3600*1.15:.2f} cluster-hours.

## Package contents

- `configuration/frozen-protocol.json`: authoritative rules.
- `matrix/condition-catalog.csv`: condition definitions and matched accuracy.
- `matrix/run-matrix.csv`: all preassigned experimental cells.
- `matrix/randomized-run-order.csv`: immutable execution sequence.
- `matrix/run-matrix.json`: machine-readable sequence.
- `analysis/statistical-analysis-plan.md`: estimands, tests, multiplicity, and missing-data rules.
- `analysis/runtime-estimate.csv`: duration and resource estimate.
- `validation/validation-summary.json`: automated completion checks.
- `manifests/SHA256SUMS.csv`: integrity ledger.

## Freeze rule

After this package is finalized, conditions, repetitions, outcomes, exclusions, and tests must not be added, removed, or changed in response to favorable or unfavorable final results. Any unavoidable operational amendment must be timestamped, justified without reference to outcomes, versioned, and preserved alongside this version.
"""
    (OUT / "STEP-14-DETAILED-REPORT.md").write_text(report, encoding="utf-8")

    sap = """# Statistical Analysis Plan

## Analysis population

The primary analysis includes all technically valid safety-disabled matched runs. The run is the unit of observation. A technical failure is not analyzed but remains in the audit ledger and is replaced only within the same preassigned matrix cell.

## Estimands

For each of seven forecast pairs, calculate B minus A within the same repetition block. The primary estimand is the median paired difference in deficient ready-replica-seconds. Positive values mean side B caused more capacity deficiency. Secondary estimands use the same direction for excess ready-replica-seconds, SLO-violation seconds, P99 latency, failure rate, completion ratio, and scale-up lateness.

## Inference

Use a two-sided exact sign-flip paired permutation test for the primary outcome when the data permit exact enumeration. Report the raw p-value and Holm-adjusted p-value across seven pair-specific primary tests. Report the paired median difference and a 95% percentile bootstrap confidence interval using seed 14002. Use the Wilcoxon signed-rank test as a sensitivity analysis; zero differences are handled with the Pratt convention.

Secondary outcomes are descriptive/exploratory: report paired median, interquartile range, mean, standard deviation, effect direction, and unadjusted 95% intervals. Do not recast secondary findings as confirmatory.

## Oracle and safety analyses

Oracle runs describe the achievable same-policy reference by workload and are not pooled into matched-error hypothesis tests. Safety-on runs are compared descriptively with their corresponding safety-off condition; because safety-on has five repetitions and safety-off has eight, use repetition blocks 1–5 for the prespecified paired safety contrast.

## Missing and outliers

No outcome imputation and no statistical outlier deletion are allowed. Technically valid extreme observations remain. Technical invalidity follows only the frozen protocol. Report the number of failed attempts, replacement attempts, and reasons by condition.
"""
    (OUT / "analysis" / "statistical-analysis-plan.md").write_text(sap, encoding="utf-8")

    failure = """# Failed-Run and Exclusion Policy

1. Validate identity, clocks, reset, collectors, workload accounting, and evidence completeness without using outcome favorability.
2. If valid, retain the run even when latency, failures, capacity deficiency, or readiness behavior is extreme.
3. If technically invalid, preserve the complete attempt directory and assign a controlled reason code.
4. Rerun the same preassigned `run_id` cell with `attempt` incremented; retain both attempts.
5. Never replace a failed cell with another condition, never silently reorder completed evidence, and never stop a condition because its results appear favorable or unfavorable.
6. Any protocol amendment requires a new version, timestamp, rationale independent of outcomes, and an amendment ledger entry.
"""
    (OUT / "FAILED-RUN-POLICY.md").write_text(failure, encoding="utf-8")

    readme = """# Step 14 Final Experimental Protocol v1.0.0

This directory is the frozen, outcome-blind specification for the final autoscaling experiments. The authoritative protocol is `configuration/frozen-protocol.json`; the execution order is `matrix/randomized-run-order.csv`.

Do not edit the matrix after final outcome collection begins. Record unavoidable operational changes in a new version and preserve this package unchanged.

Validation (using the bundled/project Python runtime):

```text
python scripts/validate_step14.py
```

Expected result: `STEP 14 VALIDATION PASSED: 142 unique frozen runs`.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    checks = []
    def check(name: str, passed: bool, details: str = "") -> None:
        checks.append({"name": name, "passed": bool(passed), "details": details})
    check("source_step12_valid", json.loads((S12 / "validation" / "validation-summary.json").read_text())["valid"])
    check("source_step13_complete", json.loads((S13 / "analysis" / "campaign-status.json").read_text())["campaign_complete"])
    check("seven_pairs", len(pairs) == 7, str(len(pairs)))
    check("total_runs_142", len(rows) == 142, str(len(rows)))
    check("unique_run_ids", len({r["run_id"] for r in rows}) == len(rows))
    check("primary_112", by_phase["primary"] == 112, str(by_phase["primary"]))
    check("oracle_20", by_phase["reference"] == 20, str(by_phase["reference"]))
    check("secondary_safety_10", by_phase["secondary_safety"] == 10, str(by_phase["secondary_safety"]))
    check("primary_safety_disabled", all(r["safety_enabled"] == "false" for r in rows if r["phase"] == "primary"))
    check("all_inputs_exist", all((ROOT / r["workload_path"]).exists() and (ROOT / r["forecast_path"]).exists() and (ROOT / r["oracle_path"]).exists() for r in rows))
    check("all_input_hashes_recomputed", all(sha256(ROOT/r["workload_path"]) == r["workload_sha256"] and sha256(ROOT/r["forecast_path"]) == r["forecast_sha256"] and sha256(ROOT/r["oracle_path"]) == r["oracle_sha256"] for r in rows))
    check("randomized_order_complete", len(ordered) == len(rows) and {r["run_id"] for r in ordered} == {r["run_id"] for r in rows})
    check("matching_tolerance_frozen", all(p["matching"]["mae_relative_difference"] < .02 and p["matching"]["rmse_relative_difference"] < .03 for p in pairs))
    check("controller_policy_hash_frozen", sha256(S9 / "configuration" / "policy-config.json") == protocol["fixed_system"]["controller_policy_sha256"])
    check("application_image_digest_frozen", "@sha256:" in protocol["fixed_system"]["application_image"])
    check("cluster_identity_frozen", len(protocol["fixed_system"]["cluster"]["nodes"]) == 3 and bool(protocol["fixed_system"]["cluster"]["kubernetes_version"]))
    check("analysis_and_exclusion_rules_frozen", bool(protocol["primary_outcome"]) and bool(protocol["analysis"]["test"]) and len(protocol["invalid_if"]) >= 10)
    valid = all(c["passed"] for c in checks)
    dump_json(OUT / "validation" / "validation-summary.json", {"schema_version": VERSION, "valid": valid, "checks": checks})

    # Reproducible entry points copied into the package.
    shutil.copy2(Path(__file__), OUT / "scripts" / "build_step14.py")
    validate_script = """from pathlib import Path\nimport json, csv, hashlib\nroot=Path(__file__).resolve().parents[1]\nv=json.loads((root/'validation/validation-summary.json').read_text())\nassert v['valid'] and all(c['passed'] for c in v['checks'])\nrows=list(csv.DictReader((root/'matrix/randomized-run-order.csv').open()))\nassert len(rows)==142 and len({r['run_id'] for r in rows})==142\nprint('STEP 14 VALIDATION PASSED: 142 unique frozen runs')\n"""
    (OUT / "scripts" / "validate_step14.py").write_text(validate_script, encoding="utf-8")

    # Write the package descriptor, then hash every final artifact except the
    # checksum ledger itself (which cannot contain its own stable hash).
    dump_json(OUT / "manifests" / "package-manifest.json", {"schema_version": VERSION, "protocol_id": protocol["protocol_id"], "run_count": len(rows), "randomization_seed": SEED, "validation_passed": valid})
    inventory = []
    for path in sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "SHA256SUMS.csv"):
        inventory.append({"path": str(path.relative_to(OUT)).replace("\\", "/"), "sha256": sha256(path), "bytes": path.stat().st_size})
    write_csv(OUT / "manifests" / "SHA256SUMS.csv", inventory)
    print(f"Built {OUT} with {len(rows)} runs; validation={valid}; planned={planned_wall/3600:.2f}h")


if __name__ == "__main__":
    main()
