from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from policy import PolicyConfig, PolicyEngine


ROOT = Path(__file__).resolve().parent.parent


def load_config() -> tuple[dict, PolicyConfig]:
    raw = json.loads((ROOT / "policy-config.json").read_text(encoding="utf-8"))
    lookup = tuple((int(k), float(v)) for k, v in sorted(raw["capacity_lookup_rps"].items(), key=lambda item: int(item[0])))
    config = PolicyConfig(
        capacity_lookup_rps=lookup,
        min_replicas=int(raw["min_replicas"]),
        max_replicas=int(raw["max_replicas"]),
        initial_replicas=int(raw["initial_replicas"]),
        safety_factor=float(raw["safety_factor"]),
        scale_down_stabilization_s=int(raw["scale_down"]["stabilization_s"]),
        decision_interval_s=int(raw["decision_interval_s"]),
        max_scale_down_step=int(raw["scale_down"]["max_step"]),
        max_scale_up_step=raw["scale_up"]["max_step"],
    )
    return raw, config


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def file_hash(path: Path) -> str:
    value = hashlib.sha256()
    value.update(path.read_bytes())
    return value.hexdigest()


def plot(trace_id: str, rows: list[dict], path: Path) -> None:
    width, height = 1800, 980
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    left, right = 115, width - 70
    top1, bottom1 = 125, 565
    top2, bottom2 = 690, 890

    def x(index: int) -> float:
        return left + (right - left) * index / max(1, len(rows) - 1)

    def y_rps(value: float) -> float:
        return bottom1 - (bottom1 - top1) * value / 70.0

    def y_pods(value: int) -> float:
        return bottom2 - (bottom2 - top2) * (value - 0.7) / 3.6

    draw.text((left, 35), "ANFA Step 8 oracle decision reference", fill="#102A43", font=font)
    draw.text((left, 65), trace_id, fill="#16697A", font=font)
    draw.rectangle((left, top1, right, bottom1), outline="#9FB3C8", width=2)
    draw.rectangle((left, top2, right, bottom2), outline="#9FB3C8", width=2)
    for tick in range(0, 71, 10):
        yy = y_rps(tick)
        draw.line((left, yy, right, yy), fill="#E6ECF0", width=1)
        draw.text((45, yy - 7), str(tick), fill="#52656D", font=font)
    future = [float(row["true_future_workload_rps"]) for row in rows]
    draw.line([(x(i), y_rps(v)) for i, v in enumerate(future)], fill="#16697A", width=4)
    for pods in range(1, 5):
        yy = y_pods(pods)
        draw.line((left, yy, right, yy), fill="#E6ECF0", width=1)
        draw.text((55, yy - 7), str(pods), fill="#52656D", font=font)
    raw = [int(row["bounded_replicas"]) for row in rows]
    commanded = [int(row["commanded_replicas"]) for row in rows]
    raw_points, command_points = [], []
    for i in range(len(rows)):
        if i:
            raw_points.append((x(i), y_pods(raw[i - 1])))
            command_points.append((x(i), y_pods(commanded[i - 1])))
        raw_points.append((x(i), y_pods(raw[i])))
        command_points.append((x(i), y_pods(commanded[i])))
    draw.line(raw_points, fill="#94A3B8", width=3)
    draw.line(command_points, fill="#7C3AED", width=4)
    draw.text((right - 420, top2 + 15), "Gray: bounded requirement", fill="#64748B", font=font)
    draw.text((right - 220, top2 + 15), "Purple: commanded", fill="#7C3AED", font=font)
    for fraction in (0, 0.25, 0.5, 0.75, 1):
        index = round((len(rows) - 1) * fraction)
        xx = x(index)
        draw.text((xx - 12, bottom2 + 18), str(index), fill="#52656D", font=font)
    draw.text((15, 325), "True t+6 workload", fill="#102A43", font=font)
    draw.text((35, 790), "Desired Pods", fill="#102A43", font=font)
    draw.text(((left + right) / 2 - 65, 940), "Decision time from T0 (seconds)", fill="#102A43", font=font)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step7-root", required=True, type=Path)
    args = parser.parse_args()
    step7 = args.step7_root.resolve()
    step7_manifest_path = step7 / "suite-manifest.json"
    step7_manifest = json.loads(step7_manifest_path.read_text(encoding="utf-8"))
    raw_config, config = load_config()
    if step7_manifest["forecast_horizon_ms"] != raw_config["forecast_horizon_s"] * 1000:
        raise ValueError("Step 7 horizon and Step 8 policy disagree")
    if step7_manifest["controller_decision_interval_ms"] != raw_config["decision_interval_s"] * 1000:
        raise ValueError("Step 7 decision interval and Step 8 policy disagree")
    if {str(k): v for k, v in config.capacity_lookup_rps} != step7_manifest["capacity_lookup_rps"]:
        raise ValueError("Step 7 capacity lookup and Step 8 policy disagree")

    for directory in ("timelines", "plots", "validation", "samples"):
        (ROOT / directory).mkdir(parents=True, exist_ok=True)

    output_records = []
    for trace in step7_manifest["traces"]:
        trace_id = trace["trace_id"]
        workload_rows = read_csv(step7 / trace["workload_file"])
        step7_oracle_rows = read_csv(step7 / trace["oracle_file"])
        if len(step7_oracle_rows) != len(workload_rows):
            raise ValueError(f"{trace_id}: Step 7 oracle row count mismatch")
        values = [float(row["target_rps"]) for row in workload_rows]
        engine = PolicyEngine(config)
        timeline = []
        horizon_steps = raw_config["forecast_horizon_s"] // raw_config["decision_interval_s"]
        for index, source in enumerate(workload_rows):
            target_index = index + horizon_steps
            terminal = target_index >= len(values)
            future_value = values[-1] if terminal else values[target_index]
            decision = engine.decide(future_value)
            if decision.raw_replicas != int(step7_oracle_rows[index]["decision_time_oracle_replicas"]):
                raise ValueError(f"{trace_id}: empirical raw oracle mismatch at decision {index}")
            timeline.append({
                "trace_id": trace_id,
                "policy_id": raw_config["policy_id"],
                "decision_seq": index,
                "decision_offset_ms": int(source["offset_ms"]),
                "forecast_issued_offset_ms": int(source["offset_ms"]),
                "forecast_target_offset_ms": int(source["offset_ms"]) + raw_config["forecast_horizon_s"] * 1000,
                "horizon_ms": raw_config["forecast_horizon_s"] * 1000,
                "true_current_workload_rps": f"{values[index]:.6f}",
                "true_future_workload_rps": f"{future_value:.6f}",
                "terminal_extension": str(terminal).lower(),
                "safety_factor": f"{config.safety_factor:.6f}",
                "safety_adjusted_workload_rps": f"{decision.safety_adjusted_workload_rps:.6f}",
                "raw_replicas": decision.raw_replicas,
                "bounded_replicas": decision.bounded_replicas,
                "stabilized_replicas": decision.stabilized_replicas,
                "prior_commanded_replicas": decision.prior_commanded_replicas,
                "commanded_replicas": decision.commanded_replicas,
                "action": decision.action,
                "scale_down_held": str(decision.scale_down_held).lower(),
                "reference_type": "oracle_desired_policy",
            })
        output_path = ROOT / "timelines" / f"{trace_id}.oracle-decisions.csv"
        write_csv(output_path, timeline)
        plot(trace_id, timeline, ROOT / "plots" / f"{trace_id}.oracle-decisions.png")
        output_records.append({
            "trace_id": trace_id,
            "source_workload_file": trace["workload_file"],
            "source_workload_sha256": file_hash(step7 / trace["workload_file"]),
            "source_step7_oracle_sha256": file_hash(step7 / trace["oracle_file"]),
            "step7_raw_oracle_verified": True,
            "oracle_timeline_file": str(output_path.relative_to(ROOT)).replace("\\", "/"),
            "decision_count": len(timeline),
            "scale_up_actions": sum(row["action"] == "scale_up" for row in timeline),
            "scale_down_actions": sum(row["action"] == "scale_down" for row in timeline),
            "held_scale_down_decisions": sum(row["scale_down_held"] == "true" for row in timeline),
        })

    manifest = {
        "oracle_suite_id": "anfa-oracle-decision-reference",
        "oracle_suite_version": "1.0.0",
        "policy_id": raw_config["policy_id"],
        "policy_config_file": "policy-config.json",
        "step7_suite_id": step7_manifest["suite_id"],
        "step7_suite_version": step7_manifest["suite_version"],
        "step7_manifest_sha256": file_hash(step7_manifest_path),
        "reference_semantics": "desired controller decisions only; Kubernetes Ready and serving capacity are runtime observations and are not synthesized",
        "timelines": output_records,
    }
    (ROOT / "oracle-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"generated": len(output_records), "output": str(ROOT)}, indent=2))


if __name__ == "__main__":
    main()
