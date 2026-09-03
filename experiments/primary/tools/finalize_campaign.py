import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CRITICAL = [
    "metadata/run-metadata.json",
    "metadata/clock-preflight.json",
    "metadata/clock-postflight.json",
    "raw/load-generator-requests.jsonl",
    "raw/controller.jsonl",
    "raw/kubernetes-snapshots.jsonl",
    "raw/kubernetes-events.json",
    "normalized/joined-timeline.csv",
    "validation/completeness-report.json",
    "validation/checksums.sha256",
    "validation/step15-validation.json",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def validation_failure(attempt_dir: Path) -> str:
    path = attempt_dir / "validation/step15-validation.json"
    if not path.exists():
        return "validation_not_produced"
    data = load_json(path)
    failed = [c for c in data.get("checks", []) if not c.get("passed")]
    if not failed:
        return "non_validation_execution_failure"
    return "; ".join(f"{c['name']}: {c.get('details', '')}" for c in failed)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args()

    matrix_path = ROOT / "matrix/primary-execution-order.csv"
    state_path = ROOT / "state/campaign-state.json"
    protocol_path = ROOT / "configuration/execution-protocol.json"
    matrix = list(csv.DictReader(matrix_path.open(encoding="utf-8")))
    state = load_json(state_path)
    protocol = load_json(protocol_path)
    runs = state["runs"]

    completed = []
    failed = []
    deviations = []
    errors = []
    valid_attempt_dirs = []

    for row in matrix:
        run_id = row["run_id"]
        entry = runs.get(run_id)
        if not entry:
            errors.append(f"missing state entry: {run_id}")
            continue
        valid_attempt = entry.get("valid_attempt")
        if entry.get("status") != "valid" or not valid_attempt:
            errors.append(f"run not valid: {run_id}")
            continue
        attempt_dir = ROOT / "results" / run_id / f"attempt-{int(valid_attempt):02d}"
        valid_attempt_dirs.append(attempt_dir)
        missing = [name for name in CRITICAL if not (attempt_dir / name).is_file()]
        if missing:
            errors.append(f"{run_id} missing: {','.join(missing)}")
            continue
        validation = load_json(attempt_dir / "validation/step15-validation.json")
        if not validation.get("valid") or any(not c.get("passed") for c in validation.get("checks", [])):
            errors.append(f"invalid validation file: {run_id} attempt {valid_attempt}")
        metadata = load_json(attempt_dir / "metadata/run-metadata.json")
        completed.append({
            "step15_sequence": row["step15_sequence"],
            "run_id": run_id,
            "phase": row["phase"],
            "pair_id": row["pair_id"],
            "condition_side": row["condition_side"],
            "forecast_condition": row["forecast_condition"],
            "workload_id": row["workload_id"],
            "repetition": row["repetition"],
            "safety_enabled": row["safety_enabled"],
            "valid_attempt": valid_attempt,
            "started_utc": metadata.get("started_utc", ""),
            "ended_utc": metadata.get("ended_utc", ""),
            "validation_valid": str(validation.get("valid", False)).lower(),
            "evidence_directory": str(attempt_dir.relative_to(ROOT)).replace("\\", "/"),
        })
        for attempt in entry.get("attempts", []):
            if attempt.get("status") in {"invalid", "aborted"}:
                failed_dir = ROOT / "results" / run_id / f"attempt-{int(attempt['attempt']):02d}"
                failed.append({
                    "step15_sequence": row["step15_sequence"],
                    "run_id": run_id,
                    "attempt": attempt["attempt"],
                    "status": attempt["status"],
                    "claimed_utc": attempt.get("claimed_utc", ""),
                    "started_utc": attempt.get("started_utc", ""),
                    "finished_utc": attempt.get("finished_utc", ""),
                    "recorded_reason": attempt.get("reason", ""),
                    "technical_detail": validation_failure(failed_dir),
                    "evidence_directory": str(failed_dir.relative_to(ROOT)).replace("\\", "/"),
                })

    expected = protocol["scope"]["planned_runs"]
    sequences = sorted(int(r["step15_sequence"]) for r in completed)
    balance = Counter((r["phase"], r["pair_id"], r["forecast_condition"], r["workload_id"]) for r in completed)
    if len(completed) != expected:
        errors.append(f"completed count {len(completed)} != {expected}")
    if sequences != list(range(1, expected + 1)):
        errors.append("accepted sequence is not exactly 1..132")
    campaign_complete = len(completed) == expected and all(
        entry.get("status") == "valid" and entry.get("valid_attempt")
        for entry in runs.values()
    )
    if state.get("active_attempt") is not None:
        errors.append("active attempt remains")
    if not state.get("paused") or not campaign_complete:
        errors.append("campaign is not paused and complete")

    if failed:
        deviations.append({
            "deviation_id": "DEV-001",
            "classification": "technical_invalid_attempts_replaced_under_protocol",
            "affected_attempts": len(failed),
            "affected_run_cells": len({r['run_id'] for r in failed}),
            "impact_on_frozen_matrix": "none",
            "handling": "Failed attempts preserved; the identical matrix cell was repeated until one attempt passed all frozen checks.",
        })
    else:
        deviations.append({
            "deviation_id": "NONE",
            "classification": "no_protocol_deviations",
            "affected_attempts": 0,
            "affected_run_cells": 0,
            "impact_on_frozen_matrix": "none",
            "handling": "not applicable",
        })

    reports = ROOT / "reports"
    validation_dir = ROOT / "validation"
    write_csv(reports / "completed-runs.csv", completed, list(completed[0]))
    failure_fields = ["step15_sequence", "run_id", "attempt", "status", "claimed_utc", "started_utc", "finished_utc", "recorded_reason", "technical_detail", "evidence_directory"]
    write_csv(reports / "failed-attempts.csv", failed, failure_fields)
    write_csv(reports / "protocol-deviations.csv", deviations, list(deviations[0]))

    audit = {
        "schema_version": "1.0.0",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "protocol_id": protocol["protocol_id"],
        "passed": not errors,
        "planned_runs": expected,
        "valid_runs": len(completed),
        "primary_runs": sum(r["phase"] == "primary" for r in completed),
        "reference_runs": sum(r["phase"] == "reference" for r in completed),
        "failed_or_aborted_attempts": len(failed),
        "run_cells_with_retries": len({r["run_id"] for r in failed}),
        "valid_attempts_with_all_critical_files": len(valid_attempt_dirs) - sum(" missing: " in e for e in errors),
        "matrix_unique_run_ids": len({r["run_id"] for r in matrix}),
        "sequence_complete": sequences == list(range(1, expected + 1)),
        "campaign_complete": campaign_complete,
        "campaign_paused": bool(state.get("paused")),
        "active_attempt": state.get("active_attempt"),
        "balance_cells": [
            {"phase": k[0], "pair_id": k[1], "forecast_condition": k[2], "workload_id": k[3], "valid_runs": v}
            for k, v in sorted(balance.items())
        ],
        "errors": errors,
    }
    validation_dir.mkdir(parents=True, exist_ok=True)
    (validation_dir / "final-campaign-audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

    if args.write_manifest:
        excluded = {
            Path("manifests/final-package-checksums.sha256"),
            Path("validation/final-campaign-audit.json"),
        }
        files = sorted(p for p in ROOT.rglob("*") if p.is_file() and p.relative_to(ROOT) not in excluded)
        manifest = ROOT / "manifests/final-package-checksums.sha256"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        with manifest.open("w", encoding="utf-8", newline="\n") as handle:
            for path in files:
                rel = path.relative_to(ROOT).as_posix()
                handle.write(f"{sha256(path)}  {rel}\n")
        audit["manifest_file_count"] = len(files)
        audit["manifest_sha256"] = sha256(manifest)
        (validation_dir / "final-campaign-audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(audit, indent=2))
    raise SystemExit(0 if audit["passed"] else 1)


if __name__ == "__main__":
    main()
