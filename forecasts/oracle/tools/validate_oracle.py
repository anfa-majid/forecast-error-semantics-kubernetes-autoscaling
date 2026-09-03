from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from policy import PolicyConfig, PolicyEngine


def digest(path: Path) -> str:
    value = hashlib.sha256()
    value.update(path.read_bytes())
    return value.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


policy = json.loads((ROOT / "policy-config.json").read_text(encoding="utf-8"))
manifest = json.loads((ROOT / "oracle-manifest.json").read_text(encoding="utf-8"))
config = PolicyConfig(
    capacity_lookup_rps=tuple((int(k), float(v)) for k, v in sorted(policy["capacity_lookup_rps"].items(), key=lambda item: int(item[0]))),
    min_replicas=policy["min_replicas"],
    max_replicas=policy["max_replicas"],
    initial_replicas=policy["initial_replicas"],
    safety_factor=policy["safety_factor"],
    scale_down_stabilization_s=policy["scale_down"]["stabilization_s"],
    decision_interval_s=policy["decision_interval_s"],
    max_scale_down_step=policy["scale_down"]["max_step"],
    max_scale_up_step=policy["scale_up"]["max_step"],
)
failures = []
manual_cases = {25.0: 1, 30.0: 1, 35.0: 2, 40.0: 2, 50.0: 3, 55.0: 3, 60.0: 4, 65.0: 4}
manual_engine = PolicyEngine(config)
for workload, expected in manual_cases.items():
    actual, _ = manual_engine.raw_replicas(workload)
    if actual != expected:
        failures.append(f"manual capacity case failed: {workload} -> {actual}, expected {expected}")

for item in manifest["timelines"]:
    path = ROOT / item["oracle_timeline_file"]
    rows = read_csv(path)
    if len(rows) != item["decision_count"]:
        failures.append(f"{item['trace_id']}: decision count mismatch")
        continue
    engine = PolicyEngine(config)
    prior = config.initial_replicas
    for index, row in enumerate(rows):
        if int(row["decision_seq"]) != index or int(row["decision_offset_ms"]) != index * 1000:
            failures.append(f"{item['trace_id']}: decision sequence mismatch at {index}")
            break
        if int(row["forecast_target_offset_ms"]) - int(row["forecast_issued_offset_ms"]) != policy["forecast_horizon_s"] * 1000:
            failures.append(f"{item['trace_id']}: horizon mismatch at {index}")
            break
        decision = engine.decide(float(row["true_future_workload_rps"]))
        expected_fields = {
            "raw_replicas": decision.raw_replicas,
            "bounded_replicas": decision.bounded_replicas,
            "stabilized_replicas": decision.stabilized_replicas,
            "prior_commanded_replicas": decision.prior_commanded_replicas,
            "commanded_replicas": decision.commanded_replicas,
        }
        if any(int(row[field]) != value for field, value in expected_fields.items()):
            failures.append(f"{item['trace_id']}: policy replay mismatch at {index}")
            break
        if int(row["commanded_replicas"]) - prior > 3 or prior - int(row["commanded_replicas"]) > 1:
            failures.append(f"{item['trace_id']}: step restriction violated at {index}")
            break
        prior = int(row["commanded_replicas"])
        if row["reference_type"] != "oracle_desired_policy":
            failures.append(f"{item['trace_id']}: readiness/desire semantics mixed")
            break

ledger = ROOT / "SHA256SUMS.csv"
if ledger.exists():
    for row in read_csv(ledger):
        path = ROOT / row["path"]
        if not path.is_file() or digest(path) != row["sha256"]:
            failures.append(f"checksum mismatch: {row['path']}")

result = {"oracle_validation_passed": not failures, "timeline_count": len(manifest["timelines"]), "manual_cases": len(manual_cases), "failures": failures}
(ROOT / "validation").mkdir(parents=True, exist_ok=True)
(ROOT / "validation" / "validation-summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, indent=2))
raise SystemExit(0 if not failures else 1)
