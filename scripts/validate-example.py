#!/usr/bin/env python3
"""Validate the evidence produced by the functional Kubernetes example."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} does not contain a JSON object")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {error}") from error
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            records.append(value)
    return records


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(run_root: Path, run_id: str, duration_seconds: int, expected_requests: int) -> dict[str, Any]:
    repository = Path(__file__).resolve().parents[1]
    inputs = run_root / "inputs"
    raw = run_root / "raw"
    normalized = run_root / "normalized"
    summary = read_json(raw / "load-generator-requests.summary.json")
    requests = read_jsonl(raw / "load-generator-requests.jsonl")
    snapshots = read_jsonl(raw / "kubernetes-snapshots.jsonl")
    controller_records = read_jsonl(raw / "controller.jsonl")
    with (inputs / "narrow-spike-v1.requests.csv").open(newline="", encoding="utf-8-sig") as handle:
        schedule = list(csv.DictReader(handle))
    with (inputs / "narrow-spike-v1.oracle-forecast.csv").open(newline="", encoding="utf-8-sig") as handle:
        forecast = list(csv.DictReader(handle))
    policy = read_json(repository / "controller" / "configuration" / "policy-config.json")

    require(summary.get("run_id") == run_id, "load-generator summary run_id does not match")
    for field in ("requests_scheduled", "requests_recorded", "completed_successfully"):
        require(summary.get(field) == expected_requests, f"{field} is not {expected_requests}")
    require(summary.get("errors") == 0, "load generator recorded errors")
    require(summary.get("timeouts") == 0, "load generator recorded timeouts")
    require(len(requests) == expected_requests, "request-record count does not match the schedule")
    require(all(row.get("run_id") == run_id for row in requests), "request records contain another run_id")
    require(all(row.get("success") is True for row in requests), "one or more requests were unsuccessful")
    require(not any(row.get("timeout") is True for row in requests), "one or more requests timed out")
    require(len({row.get("request_id") for row in requests}) == expected_requests, "request IDs are not unique")
    require(len(schedule) == expected_requests, "packaged request schedule has the wrong row count")
    scheduled = {
        row["request_id"]: (
            int(row["scheduled_offset_us"]), int(row["source_second"]),
            float(row["target_rps"]), int(row["scheduled_requests_in_second"]),
        )
        for row in schedule
    }
    observed = {
        row["request_id"]: (
            int(row["scheduled_offset_us"]), int(row["source_second"]),
            float(row["target_rps"]), int(row["scheduled_requests_in_second"]),
        )
        for row in requests
    }
    require(observed == scheduled, "request records do not match the deterministic schedule")

    require(len(snapshots) >= duration_seconds, "too few Kubernetes snapshots")
    require(all(row.get("run_id") == run_id for row in snapshots), "Kubernetes snapshots contain another run_id")
    require(not any(row.get("collection_error") for row in snapshots), "Kubernetes snapshots contain collection errors")
    sequences = [row.get("sequence") for row in snapshots]
    require(sequences == list(range(len(snapshots))), "Kubernetes snapshot sequence is not contiguous")

    decisions = [row for row in controller_records if row.get("record_type") == "decision"]
    require(all(row.get("run_id") == run_id for row in decisions), "controller decisions contain another run_id")
    require(len(decisions) == duration_seconds, "controller decision count is incorrect")
    require([int(row["decision_seq"]) for row in decisions] == list(range(duration_seconds)), "controller decision sequence is not contiguous")
    require([int(row["tick_offset_ms"]) for row in decisions] == list(range(0, duration_seconds * 1000, 1000)), "controller decision ticks are not contiguous")
    require(len(forecast) == duration_seconds, "oracle forecast has the wrong row count")
    forecast_by_tick = {int(row["issued_offset_ms"]): float(row["predicted_rps"]) for row in forecast}
    require(
        all(float(row["predicted_rps"]) == forecast_by_tick[int(row["tick_offset_ms"])] for row in decisions),
        "controller decisions do not reproduce the supplied forecast",
    )
    capacity_lookup = sorted(policy["capacity_lookup"], key=lambda row: float(row["rps"]))

    def raw_replicas(predicted_rps: float) -> int:
        for entry in capacity_lookup:
            if predicted_rps <= float(entry["rps"]):
                return int(entry["replicas"])
        return int(policy["max_replicas"])

    require(
        all(int(row["raw_replicas"]) == raw_replicas(float(row["predicted_rps"])) for row in decisions),
        "controller raw-replica decisions disagree with the pinned capacity lookup",
    )
    changes = [
        (int(row["tick_offset_ms"]) // 1000, int(row["prior_commanded_replicas"]), int(row["commanded_replicas"]), row["action"])
        for row in decisions if row["action"] != "none"
    ]
    require(
        changes == [(54, 1, 4, "scale_up"), (113, 4, 3, "scale_down"), (114, 3, 2, "scale_down"), (115, 2, 1, "scale_down")],
        "controller transitions do not match the pinned oracle example and stabilization policy",
    )
    require(all(row.get("api_result") == "success" for row in decisions if row["action"] != "none"), "a scaling API update failed")

    timeline_path = normalized / "joined-timeline.csv"
    with timeline_path.open(newline="", encoding="utf-8-sig") as handle:
        timeline = list(csv.DictReader(handle))
    require(len(timeline) == duration_seconds, "normalized timeline has the wrong row count")
    require([int(row["second"]) for row in timeline] == list(range(duration_seconds)), "timeline seconds are not contiguous")
    require(sum(int(row["dispatched_requests"]) for row in timeline) == expected_requests, "timeline dispatch total is incorrect")
    require(all(row["controller_present"].lower() == "true" for row in timeline), "timeline is missing controller decisions")
    require(all(row["kubernetes_present"].lower() == "true" for row in timeline), "timeline is missing Kubernetes observations")

    desired = [int(row["deployment"]["desired_replicas"]) for row in snapshots]
    ready = [int(row["deployment"]["ready_replicas"]) for row in snapshots]
    require(min(desired) == 1 and max(desired) == 4, "functional example did not exercise the expected 1-to-4 replica range")
    require(max(ready) == 4, "four replicas never became ready")

    return {
        "schema_version": "1.0.0",
        "valid": True,
        "run_id": run_id,
        "duration_seconds": duration_seconds,
        "requests_scheduled": summary["requests_scheduled"],
        "requests_recorded": summary["requests_recorded"],
        "requests_completed_successfully": summary["completed_successfully"],
        "request_schedule_exact": True,
        "request_errors": summary["errors"],
        "request_timeouts": summary["timeouts"],
        "maximum_dispatch_lateness_us": summary["maximum_dispatch_lateness_us"],
        "kubernetes_snapshots": len(snapshots),
        "kubernetes_collection_errors": 0,
        "controller_decisions": len(decisions),
        "forecast_decision_values_exact": True,
        "capacity_lookup_decisions_exact": True,
        "successful_scale_api_updates": len(changes),
        "timeline_rows": len(timeline),
        "minimum_desired_replicas": min(desired),
        "maximum_desired_replicas": max(desired),
        "maximum_ready_replicas": max(ready),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-directory", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--duration-seconds", type=int, default=180)
    parser.add_argument("--expected-requests", type=int, default=5550)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        report = validate(args.run_directory, args.run_id, args.duration_seconds, args.expected_requests)
    except (OSError, ValueError, KeyError, TypeError) as error:
        report = {
            "schema_version": "1.0.0",
            "valid": False,
            "run_id": args.run_id,
            "reason": str(error),
        }
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        raise SystemExit(1) from error

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
