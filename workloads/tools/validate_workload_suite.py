from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def digest(path: Path) -> str:
    value = hashlib.sha256()
    value.update(path.read_bytes())
    return value.hexdigest()


manifest = json.loads((ROOT / "suite-manifest.json").read_text(encoding="utf-8"))
capacity = {int(k): float(v) for k, v in manifest["capacity_lookup_rps"].items()}
horizon_ms = int(manifest["forecast_horizon_ms"])
failures: list[str] = []


def replicas(rps: float) -> int:
    for count, limit in capacity.items():
        if rps <= limit + 1e-9:
            return count
    raise ValueError(f"RPS {rps} is outside the validated range")


for item in manifest["traces"]:
    trace_id = item["trace_id"]
    with (ROOT / item["workload_file"]).open(newline="", encoding="utf-8") as handle:
        workload = list(csv.DictReader(handle))
    with (ROOT / item["oracle_file"]).open(newline="", encoding="utf-8") as handle:
        oracle = list(csv.DictReader(handle))
    with (ROOT / item["request_schedule_file"]).open(newline="", encoding="utf-8") as handle:
        requests = list(csv.DictReader(handle))
    annotation = json.loads((ROOT / item["annotation_file"]).read_text(encoding="utf-8"))

    if len(workload) != item["duration_s"] or len(oracle) != len(workload):
        failures.append(f"{trace_id}: row count mismatch")
        continue
    expected_offsets = [i * manifest["sample_interval_ms"] for i in range(len(workload))]
    actual_offsets = [int(row["offset_ms"]) for row in workload]
    if actual_offsets != expected_offsets:
        failures.append(f"{trace_id}: offsets are not consecutive")
    values = [float(row["target_rps"]) for row in workload]
    calculated = [replicas(value) for value in values]
    recorded = [int(row["oracle_replicas"]) for row in workload]
    if calculated != recorded:
        failures.append(f"{trace_id}: workload oracle replica mismatch")
    if max(values) > capacity[4] or min(values) <= 0:
        failures.append(f"{trace_id}: workload outside permitted range")
    for i, row in enumerate(oracle):
        if int(row["target_offset_ms"]) - int(row["decision_offset_ms"]) != horizon_ms:
            failures.append(f"{trace_id}: horizon mismatch at row {i}")
            break
        target = i + horizon_ms // manifest["sample_interval_ms"]
        expected_rps = values[-1] if target >= len(values) else values[target]
        if abs(float(row["future_target_rps"]) - expected_rps) > 1e-6:
            failures.append(f"{trace_id}: future workload mismatch at row {i}")
            break
        if int(row["decision_time_oracle_replicas"]) != replicas(expected_rps):
            failures.append(f"{trace_id}: decision-time oracle mismatch at row {i}")
            break
    if annotation["duration_s"] != len(values):
        failures.append(f"{trace_id}: annotation duration mismatch")
    if not annotation["events"]:
        failures.append(f"{trace_id}: no event annotations")
    if len(requests) != item["scheduled_request_count"]:
        failures.append(f"{trace_id}: request schedule count mismatch")
    request_offsets = [int(row["scheduled_offset_us"]) for row in requests]
    if request_offsets != sorted(request_offsets) or len(request_offsets) != len(set(request_offsets)):
        failures.append(f"{trace_id}: request offsets are not strictly ordered and unique")
    if requests and (request_offsets[0] < 0 or request_offsets[-1] >= len(values) * 1_000_000):
        failures.append(f"{trace_id}: request offset outside trace duration")
    counts = [0] * len(values)
    for row in requests:
        second = int(row["source_second"])
        counts[second] += 1
        if int(row["scheduled_requests_in_second"]) <= 0:
            failures.append(f"{trace_id}: invalid per-second request count")
            break
    cumulative_target = 0.0
    cumulative_scheduled = 0
    for second, value in enumerate(values):
        cumulative_target += value
        cumulative_scheduled += counts[second]
        if abs(cumulative_scheduled - cumulative_target) >= 1.000001:
            failures.append(f"{trace_id}: request expansion drift exceeds one request at second {second}")
            break

checksum_rows = list(csv.DictReader((ROOT / "SHA256SUMS.csv").open(newline="", encoding="utf-8")))
for row in checksum_rows:
    path = ROOT / row["path"]
    if not path.is_file() or digest(path) != row["sha256"]:
        failures.append(f"checksum mismatch: {row['path']}")

result = {
    "suite_version": manifest["suite_version"],
    "independent_validation_passed": not failures,
    "trace_count": len(manifest["traces"]),
    "failures": failures,
}
print(json.dumps(result, indent=2))
raise SystemExit(0 if not failures else 1)
