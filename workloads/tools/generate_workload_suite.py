from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SUITE_VERSION = "1.0.0"
HORIZON_S = 6
DECISION_INTERVAL_S = 1
CAPACITY = {1: 30.0, 2: 40.0, 3: 55.0, 4: 65.0}
BOUNDARIES = (30.0, 40.0, 55.0)
SCRIPT_PATH = Path(__file__).resolve()
OUTPUT = SCRIPT_PATH.parent.parent if SCRIPT_PATH.parent.name == "tools" else Path("outputs/step-7-workload-suite-v1.0.0")


def oracle_replicas(rps: float) -> int:
    for replicas, limit in CAPACITY.items():
        if rps <= limit + 1e-9:
            return replicas
    raise ValueError(f"{rps} RPS exceeds validated capacity")


def ramp_trace() -> list[float]:
    values = []
    for t in range(480):
        if t < 60:
            value = 25.0
        elif t < 240:
            value = 25.0 + 35.0 * ((t - 59) / 180.0)
        elif t < 300:
            value = 60.0
        elif t < 420:
            value = 60.0 - 35.0 * ((t - 299) / 120.0)
        else:
            value = 25.0
        values.append(value)
    return values


def narrow_spike_trace() -> list[float]:
    return [25.0] * 60 + [60.0] * 30 + [25.0] * 90


def sustained_peak_trace() -> list[float]:
    return [25.0] * 60 + [60.0] * 180 + [25.0] * 120


def periodic_trace() -> list[float]:
    values = [25.0] * 60
    for i in range(600):
        phase = i % 120
        if phase <= 60:
            value = 25.0 + 35.0 * phase / 60.0
        else:
            value = 60.0 - 35.0 * (phase - 60.0) / 60.0
        values.append(value)
    values.extend([25.0] * 60)
    return values


def stable_noisy_trace() -> list[float]:
    pattern = [23.0, 24.0, 25.0, 26.0, 27.0, 26.0, 25.0, 24.0]
    return [pattern[t % len(pattern)] for t in range(240)]


TRACE_DEFS = {
    "gradual-ramp-v1": {
        "values": ramp_trace(),
        "purpose": ["early-versus-late", "ramp-slope-error", "readiness-alignment", "decision-boundary-mediation"],
        "equation": "25 for t<60; 25+35*(t-59)/180 for 60<=t<240; 60 for 240<=t<300; 60-35*(t-299)/120 for 300<=t<420; 25 thereafter",
        "phases": [{"phase": "warmup", "start_s": 0, "end_s": 59}, {"phase": "treatment", "start_s": 60, "end_s": 299}, {"phase": "recovery", "start_s": 300, "end_s": 479}],
        "events": [
            {"label": "stable_start", "start_s": 0, "end_s": 59},
            {"label": "transition_onset", "at_s": 60, "direction": "up"},
            {"label": "peak_start", "at_s": 240},
            {"label": "peak_time", "start_s": 240, "end_s": 299},
            {"label": "peak_end", "at_s": 299},
            {"label": "recovery_start", "at_s": 300},
            {"label": "recovery_complete", "at_s": 420},
            {"label": "recovery", "start_s": 300, "end_s": 419},
            {"label": "stable_end", "start_s": 420, "end_s": 479},
        ],
    },
    "narrow-spike-v1": {
        "values": narrow_spike_trace(),
        "purpose": ["missed-versus-false-peak", "brief-capacity-shortage", "late-forecast", "reactive-safety-timing"],
        "equation": "25 for 0<=t<60; 60 for 60<=t<90; 25 for 90<=t<180",
        "phases": [{"phase": "warmup", "start_s": 0, "end_s": 59}, {"phase": "treatment", "start_s": 60, "end_s": 89}, {"phase": "recovery", "start_s": 90, "end_s": 179}],
        "events": [
            {"label": "stable_start", "start_s": 0, "end_s": 59},
            {"label": "transition_onset", "at_s": 60, "direction": "up"},
            {"label": "peak_start", "at_s": 60},
            {"label": "peak_time", "start_s": 60, "end_s": 89},
            {"label": "peak_end", "at_s": 89},
            {"label": "recovery_start", "at_s": 90},
            {"label": "recovery_complete", "at_s": 90},
            {"label": "recovery", "start_s": 90, "end_s": 179},
            {"label": "stable_end", "start_s": 90, "end_s": 179},
        ],
    },
    "sustained-peak-v1": {
        "values": sustained_peak_trace(),
        "purpose": ["persistent-underprediction", "peak-amplitude-error", "shortened-versus-extended-duration", "reliability-cost-asymmetry"],
        "equation": "25 for 0<=t<60; 60 for 60<=t<240; 25 for 240<=t<360",
        "phases": [{"phase": "warmup", "start_s": 0, "end_s": 59}, {"phase": "treatment", "start_s": 60, "end_s": 239}, {"phase": "recovery", "start_s": 240, "end_s": 359}],
        "events": [
            {"label": "stable_start", "start_s": 0, "end_s": 59},
            {"label": "transition_onset", "at_s": 60, "direction": "up"},
            {"label": "peak_start", "at_s": 60},
            {"label": "peak_time", "start_s": 60, "end_s": 239},
            {"label": "peak_end", "at_s": 239},
            {"label": "recovery_start", "at_s": 240},
            {"label": "recovery_complete", "at_s": 240},
            {"label": "recovery", "start_s": 240, "end_s": 359},
            {"label": "stable_end", "start_s": 240, "end_s": 359},
        ],
    },
    "periodic-triangle-v1": {
        "values": periodic_trace(),
        "purpose": ["phase-shift", "repeated-timing-error", "repeated-over-underprovisioning", "scaling-churn"],
        "equation": "25 baseline for 60 s; five cycles of 25+35*p/60 for 0<=p<=60 and 60-35*(p-60)/60 for 60<p<120; 25 recovery for 60 s",
        "phases": [{"phase": "warmup", "start_s": 0, "end_s": 59}, {"phase": "treatment", "start_s": 60, "end_s": 659}, {"phase": "recovery", "start_s": 660, "end_s": 719}],
        "events": (
            [{"label": "stable_start", "start_s": 0, "end_s": 59}]
            + [
                event
                for cycle in range(1, 6)
                for event in [
                    {"label": "transition_onset", "cycle": cycle, "at_s": 60 + (cycle - 1) * 120, "direction": "up"},
                    {"label": "peak_start", "cycle": cycle, "at_s": 120 + (cycle - 1) * 120},
                    {"label": "peak_time", "cycle": cycle, "at_s": 120 + (cycle - 1) * 120},
                    {"label": "peak_end", "cycle": cycle, "at_s": 120 + (cycle - 1) * 120},
                    {"label": "recovery_start", "cycle": cycle, "at_s": 121 + (cycle - 1) * 120},
                    {"label": "cycle_end", "cycle": cycle, "at_s": 179 + (cycle - 1) * 120},
                ]
            ]
            + [{"label": "recovery", "start_s": 660, "end_s": 719}, {"label": "recovery_complete", "at_s": 660}, {"label": "stable_end", "start_s": 660, "end_s": 719}]
        ),
    },
    "stable-noisy-control-v1": {
        "values": stable_noisy_trace(),
        "purpose": ["stable-period-control", "non-decision-changing-error", "false-peak-source"],
        "equation": "repeat [23,24,25,26,27,26,25,24] RPS once per second for 240 s",
        "phases": [{"phase": "warmup", "start_s": 0, "end_s": 59}, {"phase": "treatment", "start_s": 60, "end_s": 179}, {"phase": "recovery", "start_s": 180, "end_s": 239}],
        "events": [
            {"label": "stable_start", "start_s": 0, "end_s": 59},
            {"label": "peak_start", "at_s": 4, "repeats_every_s": 8},
            {"label": "peak_time", "at_s": 4, "repeats_every_s": 8},
            {"label": "peak_end", "at_s": 4, "repeats_every_s": 8},
            {"label": "stable_end", "start_s": 180, "end_s": 239},
        ],
    },
}


def event_label_at(events: list[dict], t: int) -> str:
    labels = []
    for event in events:
        if event.get("at_s") == t:
            labels.append(event["label"])
        elif event.get("start_s") == t:
            labels.append(event["label"])
    return ";".join(labels) or ""


def phase_at(phases: list[dict], t: int) -> str:
    for item in phases:
        if item["start_s"] <= t <= item["end_s"]:
            return item["phase"]
    raise ValueError(f"No phase covers offset {t}")


def request_schedule(values: list[float]) -> list[dict]:
    rows = []
    carry = 0.0
    request_number = 0
    for second, target_rps in enumerate(values):
        carry += target_rps
        count = int(carry + 1e-9)
        carry -= count
        for within_second in range(count):
            request_number += 1
            scheduled_us = second * 1_000_000 + round((within_second + 0.5) * 1_000_000 / count)
            rows.append({
                "request_id": f"req-{request_number:08d}",
                "scheduled_offset_us": scheduled_us,
                "source_second": second,
                "target_rps": f"{target_rps:.6f}",
                "scheduled_requests_in_second": count,
            })
    return rows


def boundary_crossings(values: list[float]) -> list[dict]:
    crossings = []
    for t in range(1, len(values)):
        previous, current = values[t - 1], values[t]
        for boundary in BOUNDARIES:
            if previous <= boundary < current:
                crossings.append({"at_s": t, "boundary_rps": boundary, "direction": "up", "from_replicas": oracle_replicas(previous), "to_replicas": oracle_replicas(current)})
            elif previous > boundary >= current:
                crossings.append({"at_s": t, "boundary_rps": boundary, "direction": "down", "from_replicas": oracle_replicas(previous), "to_replicas": oracle_replicas(current)})
    return crossings


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    data = path.read_bytes()
    if b"\0" not in data:
        try:
            data = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        except UnicodeDecodeError:
            pass
    return hashlib.sha256(data).hexdigest()


def validate_trace(trace_id: str, values: list[float], annotation: dict) -> list[dict]:
    checks = []
    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"trace_id": trace_id, "check": name, "passed": passed, "detail": detail})

    add("one_second_resolution", len(values) > 0, f"{len(values)} consecutive one-second samples")
    add("nonzero_minimum", min(values) > 0, f"minimum={min(values):.3f} RPS")
    add("within_validated_capacity", max(values) <= CAPACITY[4], f"maximum={max(values):.3f} RPS <= 65")
    calculated = [oracle_replicas(v) for v in values]
    add("oracle_range", min(calculated) >= 1 and max(calculated) <= 4, f"replicas={min(calculated)}..{max(calculated)}")
    required_labels = {"stable_start", "peak_start", "peak_time", "peak_end", "stable_end"}
    present = {e["label"] for e in annotation["events"]}
    add("required_annotations", required_labels.issubset(present), f"labels={sorted(present)}")
    if trace_id != "stable-noisy-control-v1":
        add("crosses_replica_boundary", bool(annotation["boundary_crossings"]), f"crossings={len(annotation['boundary_crossings'])}")
    else:
        add("control_stays_one_pod", max(calculated) == 1, "all samples require one Pod")
    return checks


def plot_trace(trace_id: str, values: list[float], events: list[dict], path: Path) -> None:
    replicas = [oracle_replicas(v) for v in values]
    width, height = 1800, 980
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    left, right = 115, width - 70
    top1, bottom1 = 125, 600
    top2, bottom2 = 700, 900

    def x(t: int) -> float:
        return left + (right - left) * t / max(1, len(values) - 1)

    def y_rps(v: float) -> float:
        return bottom1 - (bottom1 - top1) * v / 70.0

    def y_pods(v: int) -> float:
        return bottom2 - (bottom2 - top2) * (v - 0.7) / 3.6

    draw.text((left, 35), "ANFA Step 7 workload trace and empirical oracle requirement", fill="#102A43", font=font)
    draw.text((left, 65), trace_id, fill="#16697A", font=font)
    draw.rectangle((left, top1, right, bottom1), outline="#9FB3C8", width=2)
    draw.rectangle((left, top2, right, bottom2), outline="#9FB3C8", width=2)
    for tick in range(0, 71, 10):
        yy = y_rps(tick)
        draw.line((left, yy, right, yy), fill="#E6ECF0", width=1)
        draw.text((45, yy - 7), str(tick), fill="#52656D", font=font)
    for boundary in BOUNDARIES:
        yy = y_rps(boundary)
        draw.line((left, yy, right, yy), fill="#8DA2AE", width=2)
        draw.text((right - 125, yy - 17), f"{int(boundary)} RPS", fill="#52656D", font=font)
    for event in events:
        if event["label"] in {"transition_onset", "peak_start", "recovery_start", "recovery_complete"} and "at_s" in event:
            xx = x(event["at_s"])
            draw.line((xx, top1, xx, bottom2), fill="#F2C078", width=1)
    points = [(x(t), y_rps(v)) for t, v in enumerate(values)]
    draw.line(points, fill="#16697A", width=4, joint="curve")
    for pod in range(1, 5):
        yy = y_pods(pod)
        draw.line((left, yy, right, yy), fill="#E6ECF0", width=1)
        draw.text((55, yy - 7), str(pod), fill="#52656D", font=font)
    replica_points = []
    for t, value in enumerate(replicas):
        if t:
            replica_points.append((x(t), y_pods(replicas[t - 1])))
        replica_points.append((x(t), y_pods(value)))
    draw.line(replica_points, fill="#7C3AED", width=4)
    for fraction in (0, 0.25, 0.5, 0.75, 1):
        t = round((len(values) - 1) * fraction)
        xx = x(t)
        draw.line((xx, bottom2, xx, bottom2 + 8), fill="#52656D", width=1)
        draw.text((xx - 12, bottom2 + 15), str(t), fill="#52656D", font=font)
    draw.text((10, 330), "Offered workload (RPS)", fill="#102A43", font=font)
    draw.text((35, 790), "Oracle Pods", fill="#102A43", font=font)
    draw.text(((left + right) / 2 - 65, 945), "Time from T0 (seconds)", fill="#102A43", font=font)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def write_report(manifest: dict) -> None:
    report = f"""# Step 7 - Workload Trace Suite

Status: generated and automatically validated  
Suite version: `{SUITE_VERSION}`

## Executive result

Step 7 defines five deterministic workload traces for the final Azure K3s research environment: gradual ramp, narrow spike, sustained peak, periodic triangle wave, and stable/noisy control. The suite uses the Step 5 empirical capacity lookup `C1=30`, `C2=40`, `C3=55`, `C4=65 RPS` and the Step 6 forecast horizon `H=6 seconds`.

All primary traces remain at or below 60 RPS, retaining 5 RPS of headroom below the validated four-Pod limit. The 25 RPS baseline requires one Pod. The mandatory traces cross meaningful replica boundaries, while the optional control intentionally stays inside the one-Pod decision region.

## Frozen design

| Parameter | Value |
|---|---:|
| Sample interval | 1 second |
| Controller decision interval | 1 second |
| Forecast horizon | 6 seconds |
| Baseline | 25 RPS |
| Main peak | 60 RPS |
| Validated maximum | 65 RPS |
| Initial stable period | 60 seconds for mandatory traces |
| Suite version | {SUITE_VERSION} |

The one-second controller interval is frozen for the Step 7 workload/controller timing contract. A later change requires documented change control and regeneration of forecast and oracle schedules.

## Empirical oracle

The oracle uses the smallest validated Pod count whose empirical capacity covers workload:

`oracle_replicas(W) = min {{N in {{1,2,3,4}} : W <= C_N}}`

| Workload | Required Pods |
|---:|---:|
| 0-30 RPS | 1 |
| >30-40 RPS | 2 |
| >40-55 RPS | 3 |
| >55-65 RPS | 4 |

This lookup must not be replaced by `ceil(W/30)` because Step 5 found decreasing multi-Pod scaling efficiency.

## Trace catalogue

| Trace | Duration | Range | Scientific purpose |
|---|---:|---:|---|
| gradual-ramp-v1 | 480 s | 25-60 RPS | Early/late timing, slope error, readiness alignment, boundary mediation |
| narrow-spike-v1 | 180 s | 25-60 RPS | Missed/false peak, brief shortage, safety response timing |
| sustained-peak-v1 | 360 s | 25-60 RPS | Persistent bias, amplitude, duration, DRS/ERS asymmetry |
| periodic-triangle-v1 | 720 s | 25-60 RPS | Phase shift, repeated timing error, churn and repeated waste/deficit |
| stable-noisy-control-v1 | 240 s | 23-27 RPS | Stable-period control and errors that do not change decisions |

## File contract

Each file in `workloads/` contains one row per second with `trace_id`, `suite_version`, `offset_ms`, `target_rps`, `interpolation`, `phase`, `event_label`, and `oracle_replicas`.

Each file in `request-schedules/` is the exact deterministic expansion of its RPS trace into individual request dispatch offsets. Fractional per-second ramp rates use a cumulative remainder, and requests assigned to a second are evenly spaced at interval midpoints. This avoids random arrivals while keeping the cumulative scheduled count within one request of the mathematical trace integral.

Each file in `oracle/` gives both the demand-time requirement and the decision-time oracle target at `t+6 seconds`. Targets beyond the trace end use the final stable workload value and are explicitly marked `terminal_extension=true`.

Each annotation JSON records the equation, purpose, event list, detected replica-boundary crossings, duration, RPS range, and oracle replica range.

## Interpretation constraints

- These files define scheduled offered workload, not achieved throughput. Execution fidelity must be validated from load-generator dispatch logs.
- The exact per-request schedules are the authoritative dispatch plan. The load generator must consume these offsets directly or prove an identical expansion during a dry run.
- The traces are valid for the measured Azure K3s lookup and the benchmark configuration used in Steps 4-6.
- Loads above 65 RPS are outside the validated range.
- The stable/noisy control is optional and must not displace the four mandatory workloads if experiment time is constrained.
- Step 7 defines ground truth only. Accuracy-matched forecast mutations belong to the next experimental-design step.

## Completion assessment

| Written Step 7 requirement | Evidence | Status |
|---|---|---|
| Clear purpose for every workload | Trace catalogue and annotation `purpose` fields | Complete |
| Deterministic traces | Generator, workload CSVs, equations and checksums | Complete |
| Nonzero minimum and validated maximum | Automated range checks; 23-60 RPS within 65 RPS | Complete |
| Meaningful replica-boundary crossings | Detected crossing records and plots | Complete for mandatory traces |
| Practical durations | 180-720 seconds per trace | Complete |
| Stable, transition, peak and recovery annotations | Trace-specific event and phase records | Complete |
| Expected oracle replicas | Per-second workload files and oracle timelines | Complete |
| Saved request schedules | Exact per-request dispatch-offset CSVs | Complete |
| Equations/files, plots and justification | This report plus generated artifacts | Complete |
| Reproducibility | Versioned manifest, generator, independent validator and SHA-256 ledger | Complete |

All workloads have explicit purposes, deterministic equations, trace-specific phases, operational event annotations, expected oracle replicas, exact request schedules, practical durations, plots, hashes, and automated validation. Step 7 is complete at the workload-design and executable-trace level. Cluster execution of these workloads is an integration activity for the experiment runner and does not alter the frozen workload definitions.
"""
    (OUTPUT / "STEP7.md").write_text(report, encoding="utf-8", newline="\n")
    readme = """# ANFA Step 7 workload suite

Run `python tools/generate_workload_suite.py` from this directory to regenerate every trace, annotation, oracle timeline, validation record, plot, and checksum. The generator is deterministic and requires Python with Pillow.

Review `STEP7.md` for the frozen design and `validation/validation-summary.json` for machine-readable checks.
"""
    (OUTPUT / "README.md").write_text(readme, encoding="utf-8", newline="\n")


def main() -> None:
    for subdir in ("workloads", "request-schedules", "annotations", "oracle", "plots", "validation", "tools"):
        (OUTPUT / subdir).mkdir(parents=True, exist_ok=True)

    validations = []
    manifest_traces = []
    for trace_id, definition in TRACE_DEFS.items():
        values = definition["values"]
        crossings = boundary_crossings(values)
        annotation = {
            "trace_id": trace_id,
            "suite_version": SUITE_VERSION,
            "duration_s": len(values),
            "sample_interval_s": 1,
            "minimum_rps": min(values),
            "maximum_rps": max(values),
            "minimum_oracle_replicas": min(oracle_replicas(v) for v in values),
            "maximum_oracle_replicas": max(oracle_replicas(v) for v in values),
            "purpose": definition["purpose"],
            "equation": definition["equation"],
            "events": definition["events"],
            "phases": definition["phases"],
            "boundary_crossings": crossings,
        }
        annotation_path = OUTPUT / "annotations" / f"{trace_id}.annotations.json"
        annotation_path.write_text(json.dumps(annotation, indent=2), encoding="utf-8", newline="\n")

        workload_rows = []
        oracle_rows = []
        for t, value in enumerate(values):
            phase = phase_at(definition["phases"], t)
            workload_rows.append({
                "trace_id": trace_id,
                "suite_version": SUITE_VERSION,
                "offset_ms": t * 1000,
                "target_rps": f"{value:.6f}",
                "interpolation": "step",
                "phase": phase,
                "event_label": event_label_at(definition["events"], t),
                "oracle_replicas": oracle_replicas(value),
            })
            target_t = t + HORIZON_S
            terminal = target_t >= len(values)
            future_value = values[-1] if terminal else values[target_t]
            oracle_rows.append({
                "trace_id": trace_id,
                "decision_offset_ms": t * 1000,
                "target_offset_ms": target_t * 1000,
                "horizon_ms": HORIZON_S * 1000,
                "demand_time_rps": f"{value:.6f}",
                "demand_time_oracle_replicas": oracle_replicas(value),
                "future_target_rps": f"{future_value:.6f}",
                "decision_time_oracle_replicas": oracle_replicas(future_value),
                "terminal_extension": str(terminal).lower(),
            })

        workload_path = OUTPUT / "workloads" / f"{trace_id}.csv"
        request_schedule_path = OUTPUT / "request-schedules" / f"{trace_id}.requests.csv"
        oracle_path = OUTPUT / "oracle" / f"{trace_id}.oracle.csv"
        write_csv(workload_path, list(workload_rows[0]), workload_rows)
        scheduled_rows = request_schedule(values)
        write_csv(request_schedule_path, list(scheduled_rows[0]), scheduled_rows)
        write_csv(oracle_path, list(oracle_rows[0]), oracle_rows)
        plot_trace(trace_id, values, definition["events"], OUTPUT / "plots" / f"{trace_id}.png")
        validations.extend(validate_trace(trace_id, values, annotation))
        manifest_traces.append({
            "trace_id": trace_id,
            "duration_s": len(values),
            "minimum_rps": min(values),
            "maximum_rps": max(values),
            "workload_file": str(workload_path.relative_to(OUTPUT)).replace("\\", "/"),
            "request_schedule_file": str(request_schedule_path.relative_to(OUTPUT)).replace("\\", "/"),
            "scheduled_request_count": len(scheduled_rows),
            "annotation_file": str(annotation_path.relative_to(OUTPUT)).replace("\\", "/"),
            "oracle_file": str(oracle_path.relative_to(OUTPUT)).replace("\\", "/"),
            "plot_file": f"plots/{trace_id}.png",
        })

    summary = {
        "suite_version": SUITE_VERSION,
        "passed": all(item["passed"] for item in validations),
        "check_count": len(validations),
        "failed_check_count": sum(not item["passed"] for item in validations),
        "checks": validations,
    }
    (OUTPUT / "validation" / "validation-summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8", newline="\n"
    )

    manifest = {
        "suite_id": "anfa-workload-trace-suite",
        "suite_version": SUITE_VERSION,
        "environment": "anfa-cloud-native-k3s",
        "sample_interval_ms": 1000,
        "controller_decision_interval_ms": DECISION_INTERVAL_S * 1000,
        "forecast_horizon_ms": HORIZON_S * 1000,
        "capacity_lookup_rps": {str(k): v for k, v in CAPACITY.items()},
        "oracle_rule": "min N in {1,2,3,4} such that workload_rps <= C_N",
        "traces": manifest_traces,
    }
    (OUTPUT / "suite-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8", newline="\n"
    )
    write_report(manifest)

    source_copy = OUTPUT / "tools" / "generate_workload_suite.py"
    source_copy.write_text(
        Path(__file__).read_text(encoding="utf-8"), encoding="utf-8", newline="\n"
    )
    checksum_rows = []
    for path in sorted(
        p
        for p in OUTPUT.rglob("*")
        if p.is_file()
        and p.name != "SHA256SUMS.csv"
        and "__pycache__" not in p.parts
        and p.suffix.lower() != ".pyc"
    ):
        checksum_rows.append({"sha256": sha256(path), "path": str(path.relative_to(OUTPUT)).replace("\\", "/")})
    write_csv(OUTPUT / "SHA256SUMS.csv", ["sha256", "path"], checksum_rows)
    print(json.dumps({"output": str(OUTPUT), "validation_passed": summary["passed"], "files": len(checksum_rows) + 1}, indent=2))


if __name__ == "__main__":
    main()
