from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEP5 = ROOT / "step5"
RUNS = STEP5 / "runs"
REPORT = STEP5 / "report"
FIGURES = REPORT / "figures"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path):
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def classify_run(run: Path, replicas: int, rps: int) -> dict:
    rows = read_csv(run / "summary.csv")
    row = next(item for item in rows if int(item["target_rps"]) == rps)
    point = run / f"rps-{rps:03d}"
    client = load_json(point / "client-summary.json")
    cpu_path = point / "prometheus-cpu-by-pod.json"
    throttle_path = point / "prometheus-throttling-by-pod.json"
    if replicas == 1 and not cpu_path.exists():
        cpu_path = point / "prometheus-cpu.json"
    if replicas == 1 and not throttle_path.exists():
        throttle_path = point / "prometheus-throttling.json"
    cpu = load_json(cpu_path)
    throttle = load_json(throttle_path)
    cpu_values = [float(item["value"][1]) for item in cpu["data"]["result"]]
    throttle_values = [float(item["value"][1]) for item in throttle["data"]["result"]]
    pod_counts = [int(value) for value in client["serving_pods"].values()]
    reasons = []
    if float(row["p99_ms"]) > 300:
        reasons.append("p99")
    if float(row["failure_rate"]) >= 0.01:
        reasons.append("failures")
    if float(row["completion_ratio"]) < 0.99:
        reasons.append("throughput")
    if max(cpu_values, default=0) > 0.45:
        reasons.append("cpu")
    if max(throttle_values, default=0) >= 0.10:
        reasons.append("throttling")
    if len(pod_counts) != replicas:
        reasons.append("pod-coverage")
    imbalance = 0.0
    if pod_counts:
        imbalance = (max(pod_counts) - min(pod_counts)) / statistics.mean(pod_counts)
    return {
        "run": run.name,
        "replicas": replicas,
        "target_rps": rps,
        "completed": int(row["completed"]),
        "errors": int(row["errors"]),
        "failure_rate": float(row["failure_rate"]),
        "completion_ratio": float(row["completion_ratio"]),
        "achieved_rps": float(row["achieved_rps"]),
        "average_ms": float(row["average_ms"]),
        "p50_ms": float(row["p50_ms"]),
        "p95_ms": float(row["p95_ms"]),
        "p99_ms": float(row["p99_ms"]),
        "max_pod_cpu": max(cpu_values, default=0),
        "max_throttle_ratio": max(throttle_values, default=0),
        "pod_count": len(pod_counts),
        "imbalance_ratio": imbalance,
        "pass": not reasons,
        "reasons": ",".join(reasons),
    }


def collect(pattern: str, replicas: int, rates: list[int]) -> list[dict]:
    rows = []
    for run in sorted(RUNS.glob(pattern)):
        for rate in rates:
            if (run / f"rps-{rate:03d}" / "client-summary.json").exists():
                rows.append(classify_run(run, replicas, rate))
    return rows


def aggregate(rows: list[dict]) -> list[dict]:
    result = []
    for replicas, rps in sorted({(r["replicas"], r["target_rps"]) for r in rows}):
        group = [r for r in rows if r["replicas"] == replicas and r["target_rps"] == rps]
        result.append({
            "replicas": replicas,
            "target_rps": rps,
            "runs": len(group),
            "passes": sum(r["pass"] for r in group),
            "all_pass": all(r["pass"] for r in group),
            "max_failure_rate": max(r["failure_rate"] for r in group),
            "max_p99_ms": max(r["p99_ms"] for r in group),
            "max_pod_cpu": max(r["max_pod_cpu"] for r in group),
            "max_throttle_ratio": max(r["max_throttle_ratio"] for r in group),
            "max_imbalance_ratio": max(r["imbalance_ratio"] for r in group),
            "mean_achieved_rps": statistics.mean(r["achieved_rps"] for r in group),
        })
    return result


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def line_chart(path: Path, title: str, xlabel: str, ylabel: str, series: list[tuple[str, list[float], list[float], str]], reference: tuple[float, str] | None = None) -> None:
    width, height = 900, 520
    left, right, top, bottom = 90, 30, 65, 75
    xs = [x for _, sx, _, _ in series for x in sx]
    ys = [y for _, _, sy, _ in series for y in sy]
    if reference:
        ys.append(reference[0])
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = 0.0, max(ys) * 1.1 if max(ys) else 1.0
    px = lambda x: left + (x - xmin) / (xmax - xmin or 1) * (width - left - right)
    py = lambda y: top + (ymax - y) / (ymax - ymin or 1) * (height - top - bottom)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>', '<style>text{font-family:Arial,sans-serif;fill:#172033}.title{font-size:22px;font-weight:700}.axis{font-size:13px}.legend{font-size:12px}</style>', f'<text x="{width/2}" y="32" text-anchor="middle" class="title">{title}</text>']
    for i in range(6):
        y = ymin + (ymax - ymin) * i / 5
        yy = py(y)
        parts += [f'<line x1="{left}" y1="{yy}" x2="{width-right}" y2="{yy}" stroke="#e5e7eb"/>', f'<text x="{left-10}" y="{yy+4}" text-anchor="end" class="axis">{y:.1f}</text>']
    for x in sorted(set(xs)):
        xx = px(x)
        parts += [f'<line x1="{xx}" y1="{top}" x2="{xx}" y2="{height-bottom}" stroke="#f1f5f9"/>', f'<text x="{xx}" y="{height-bottom+22}" text-anchor="middle" class="axis">{x:g}</text>']
    parts += [f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#111827"/>', f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#111827"/>']
    if reference:
        yy = py(reference[0])
        parts += [f'<line x1="{left}" y1="{yy}" x2="{width-right}" y2="{yy}" stroke="#b91c1c" stroke-dasharray="7 5"/>', f'<text x="{width-right-5}" y="{yy-7}" text-anchor="end" class="legend">{reference[1]}</text>']
    legend_y = 55
    for index, (label, sx, sy, color) in enumerate(series):
        points = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in zip(sx, sy))
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3"/>')
        for x, y in zip(sx, sy):
            parts.append(f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="4" fill="{color}"/>')
        lx = left + index * 180
        parts += [f'<line x1="{lx}" y1="{legend_y}" x2="{lx+24}" y2="{legend_y}" stroke="{color}" stroke-width="3"/>', f'<text x="{lx+30}" y="{legend_y+4}" class="legend">{label}</text>']
    parts += [f'<text x="{width/2}" y="{height-20}" text-anchor="middle" class="axis">{xlabel}</text>', f'<text x="22" y="{height/2}" text-anchor="middle" transform="rotate(-90 22 {height/2})" class="axis">{ylabel}</text>', '</svg>']
    path.write_text("".join(parts), encoding="utf-8")


def make_figures(single: list[dict], multipod: list[dict]) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)

    by_rate = {}
    for row in single:
        by_rate.setdefault(row["target_rps"], []).append(row)
    rates = sorted(by_rate)
    p50 = [max(r["p50_ms"] for r in by_rate[x]) for x in rates]
    p95 = [max(r["p95_ms"] for r in by_rate[x]) for x in rates]
    p99 = [max(r["p99_ms"] for r in by_rate[x]) for x in rates]
    line_chart(FIGURES / "single-pod-latency.svg", "Single-Pod Latency Boundary", "Offered load (RPS)", "Maximum client latency (ms)", [("P50", rates, p50, "#2563eb"), ("P95", rates, p95, "#7c3aed"), ("P99", rates, p99, "#dc2626")], (300, "P99 SLO = 300 ms"))

    throttle = [100 * max(r["max_throttle_ratio"] for r in by_rate[x]) for x in rates]
    line_chart(FIGURES / "single-pod-throttling.svg", "Single-Pod CPU Throttling Boundary", "Offered load (RPS)", "Maximum throttled-period ratio (%)", [("Throttling", rates, throttle, "#7c3aed")], (10, "Guardrail = 10%"))

    capacities = {1: 45, 2: 90, 3: 105, 4: 130}
    ns = list(capacities)
    observed = [capacities[n] for n in ns]
    ideal = [45 * n for n in ns]
    line_chart(FIGURES / "capacity-scaling.svg", "Observed Versus Ideal Scaling", "Ready benchmark Pods", "Safe aggregate capacity (RPS)", [("Ideal N × 45", ns, ideal, "#64748b"), ("Observed", ns, observed, "#166534")])

    n4 = [r for r in multipod if r["replicas"] == 4]
    n4_by_rate = {}
    for row in n4:
        n4_by_rate.setdefault(row["target_rps"], []).append(row)
    r4 = sorted(n4_by_rate)
    failure = [100 * max(r["failure_rate"] for r in n4_by_rate[x]) for x in r4]
    line_chart(FIGURES / "four-pod-failures.svg", "Four-Pod Shared-Path Saturation", "Offered load (RPS)", "Maximum failure rate (%)", [("Failure rate", r4, failure, "#dc2626")], (1, "Failure SLO = 1%"))


def main() -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    single = []
    single += collect("confirmatory-lower-045-r*", 1, [45])
    single += collect("confirmatory-lower-050-r*", 1, [50])
    single += collect("confirmatory-r0*", 1, [55, 60, 65, 70, 75])

    multipod = []
    multipod += collect("multipod-n2-r*", 2, [81, 90, 99])
    multipod += collect("multipod-n3-r*", 3, [122, 135, 149])
    multipod += collect("multipod-adaptive-low-n3-r*", 3, [110, 115, 120])
    multipod += collect("multipod-adaptive-final-n3-r*", 3, [100, 105])
    multipod += collect("multipod-n4-r*", 4, [162, 180, 198])
    multipod += collect("multipod-adaptive-n4-r*", 4, [110, 120, 130])
    multipod += collect("multipod-adaptive-high-n4-r*", 4, [140, 150, 160])
    multipod += collect("multipod-adaptive-final-n4-r*", 4, [135])

    all_rows = single + multipod
    summary = aggregate(all_rows)
    write_csv(REPORT / "all-classified-runs.csv", all_rows)
    write_csv(REPORT / "aggregate-by-replicas-and-load.csv", summary)
    make_figures(single, multipod)

    capacities = {1: 45, 2: 90, 3: 105, 4: 130}
    result = {
        "c_pod_rps": 45,
        "capacity_lookup_rps": capacities,
        "scaling_efficiency": {str(n): capacities[n] / (n * 45) for n in capacities},
        "validated_replica_range": [1, 4],
        "slo": {"p99_ms_lte": 300, "failure_rate_lt": 0.01},
        "guardrails": {"throughput_fidelity_gte": 0.99, "mean_cpu_limit_fraction_lte": 0.9, "cpu_throttling_ratio_lt": 0.1},
    }
    (REPORT / "capacity-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
