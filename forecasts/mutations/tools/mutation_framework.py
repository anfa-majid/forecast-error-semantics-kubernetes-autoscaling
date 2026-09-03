from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

VERSION = "1.0.0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


@dataclass(frozen=True)
class Policy:
    policy_id: str
    capacities: tuple[tuple[int, float], ...]
    horizon_s: int
    interval_s: int
    minimum: int
    maximum: int
    initial: int
    safety_factor: float
    stabilization_s: int
    max_down_step: int

    @classmethod
    def load(cls, path: Path) -> "Policy":
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        capacities = (tuple((int(x["replicas"]), float(x["rps"])) for x in raw["capacity_lookup"])
                      if "capacity_lookup" in raw else tuple((int(k), float(v)) for k,v in raw["capacity_lookup_rps"].items()))
        return cls(raw["policy_id"], capacities,
                   int(raw.get("forecast_horizon_seconds",raw.get("forecast_horizon_s"))), int(raw.get("decision_interval_seconds",raw.get("decision_interval_s"))),
                   int(raw["min_replicas"]), int(raw["max_replicas"]), int(raw["initial_replicas"]),
                   float(raw["safety_factor"]), int(raw.get("scale_down_stabilization_seconds",raw.get("scale_down",{}).get("stabilization_s"))),
                   int(raw.get("max_scale_down_step",raw.get("scale_down",{}).get("max_step"))))

    def raw(self, rps: float) -> int:
        adjusted = self.safety_factor * rps
        for replicas, capacity in self.capacities:
            if adjusted <= capacity + 1e-9:
                return replicas
        raise ValueError(f"forecast {rps} exceeds validated capacity {self.capacities[-1][1]}")

    def replay(self, values: list[float]) -> list[dict]:
        history: deque[int] = deque(maxlen=max(1, self.stabilization_s // self.interval_s))
        prior = self.initial; rows = []
        for sequence, value in enumerate(values):
            raw = self.raw(value); bounded = min(self.maximum, max(self.minimum, raw)); history.append(bounded)
            stabilized = max(history)
            if bounded > prior:
                command, action, held = bounded, "scale_up", False
            elif stabilized < prior:
                command, action, held = max(stabilized, prior - self.max_down_step), "scale_down", False
            else:
                command, action, held = prior, "none", bounded < prior
            rows.append({"decision_seq":sequence,"decision_offset_ms":sequence*self.interval_s*1000,
                         "predicted_rps":f"{value:.6f}","raw_replicas":raw,"bounded_replicas":bounded,
                         "stabilized_replicas":stabilized,"prior_commanded_replicas":prior,
                         "commanded_replicas":command,"action":action,"scale_down_held":str(held).lower()})
            prior = command
        return rows


def load_workload(path: Path) -> tuple[list[float], list[dict]]:
    rows = read_csv(path)
    offsets = [int(row["offset_ms"]) for row in rows]
    if offsets != list(range(0, len(rows) * 1000, 1000)):
        raise ValueError(f"nonconsecutive workload offsets: {path}")
    return [float(row["target_rps"]) for row in rows], rows


def value_at(values: list[float], second: int) -> float:
    return values[min(max(second, 0), len(values) - 1)]


def oracle_forecast(values: list[float], horizon_s: int) -> tuple[list[int], list[float]]:
    targets = [second + horizon_s for second in range(len(values))]
    return targets, [value_at(values, second) for second in targets]


def inclusive(start: int, end: int) -> set[int]:
    if start > end:
        raise ValueError(f"invalid interval {start}..{end}")
    return set(range(start, end + 1))


def mutate(base_by_target: dict[int, float], spec: dict, valid_min: float, valid_max: float) -> tuple[dict[int, float], set[int]]:
    output = dict(base_by_target); p = spec["parameters"]; kind = spec["type"]; support: set[int]
    if kind in {"add_bias", "amplitude_scale", "slope_scale", "replace_interval"}:
        support = inclusive(int(p["start_s"]), int(p["end_s"]))
        for t in support & output.keys():
            if kind == "add_bias": output[t] += float(p["bias_rps"])
            elif kind in {"amplitude_scale", "slope_scale"}:
                baseline = float(p["baseline_rps"]); output[t] = baseline + float(p["factor"]) * (output[t] - baseline)
            else: output[t] = float(p["replacement_rps"])
    elif kind == "shorten_event":
        end = int(p["event_end_s"]); support = inclusive(end - int(p["shorten_s"]) + 1, end)
        for t in support & output.keys(): output[t] = float(p["baseline_rps"])
    elif kind == "extend_event":
        end = int(p["event_end_s"]); support = inclusive(end + 1, end + int(p["extend_s"]))
        for t in support & output.keys(): output[t] = float(p["peak_rps"])
    elif kind == "shift_event":
        start, end, shift = int(p["event_start_s"]), int(p["event_end_s"]), int(p["shift_s"])
        support = inclusive(start + min(0, shift), end + max(0, shift)); baseline = min(base_by_target.values())
        for t in support & output.keys():
            source = t - shift
            output[t] = base_by_target.get(source, baseline) if start <= source <= end else baseline
    elif kind == "global_shift":
        shift = int(p["shift_s"]); support = set(output)
        for t in support: output[t] = value_at([base_by_target[k] for k in sorted(base_by_target)], (t - shift) - min(base_by_target))
    elif kind == "moving_average":
        start, end, radius = int(p["event_start_s"]), int(p["event_end_s"]), int(p["radius_s"])
        support = inclusive(start - radius, end + radius)
        keys = sorted(base_by_target); low, high = keys[0], keys[-1]
        for t in support & output.keys():
            samples = [base_by_target[min(high, max(low, x))] for x in range(t-radius, t+radius+1)]
            output[t] = sum(samples) / len(samples)
    else:
        raise ValueError(f"unsupported mutation type: {kind}")
    for t, value in output.items():
        if not math.isfinite(value) or value < valid_min - 1e-9 or value > valid_max + 1e-9:
            raise ValueError(f"{spec['id']} produced out-of-range value {value} at target second {t}")
        output[t] = round(value, 6)
    return output, support


def intervals(seconds: Iterable[int]) -> list[dict]:
    values = sorted(set(seconds))
    if not values: return []
    result=[]; start=prior=values[0]
    for value in values[1:]:
        if value != prior + 1:
            result.append({"start_s":start,"end_s":prior}); start=value
        prior=value
    result.append({"start_s":start,"end_s":prior}); return result


def metrics(base: list[float], mutated: list[float], target_s: list[int], support: set[int], oracle_policy: list[dict], mutated_policy: list[dict]) -> dict:
    residual = [m-b for b,m in zip(base,mutated)]; n=len(base)
    region=[i for i,t in enumerate(target_s) if t in support]
    oracle_peak=max(base); forecast_peak=max(mutated)
    threshold=(min(base)+max(base))/2
    oracle_duration=sum(v>threshold for v in base); forecast_duration=sum(v>threshold for v in mutated)
    oracle_commands=[int(x["commanded_replicas"]) for x in oracle_policy]; commands=[int(x["commanded_replicas"]) for x in mutated_policy]
    return {
        "mae_rps":round(sum(abs(x) for x in residual)/n,6),
        "rmse_rps":round(math.sqrt(sum(x*x for x in residual)/n),6),
        "signed_bias_rps":round(sum(residual)/n,6),
        "maximum_absolute_error_rps":round(max(abs(x) for x in residual),6),
        "region_mae_rps":round(sum(abs(residual[i]) for i in region)/len(region),6) if region else 0.0,
        "changed_decisions":sum(abs(x)>1e-9 for x in residual),
        "peak_timing_error_s":target_s[mutated.index(forecast_peak)]-target_s[base.index(oracle_peak)],
        "peak_amplitude_error_rps":round(forecast_peak-oracle_peak,6),
        "duration_error_s":forecast_duration-oracle_duration,
        "replica_disagreement_seconds":sum(a!=b for a,b in zip(oracle_commands,commands)),
        "excess_replica_seconds":sum(max(b-a,0) for a,b in zip(oracle_commands,commands)),
        "deficient_replica_seconds":sum(max(a-b,0) for a,b in zip(oracle_commands,commands)),
        "false_scale_out_seconds":sum(b>a for a,b in zip(oracle_commands,commands)),
        "missed_scale_out_seconds":sum(b<a for a,b in zip(oracle_commands,commands))
    }


def points(values: list[float], width: int, height: int, left: int, top: int, minimum: float, maximum: float) -> str:
    span=max(maximum-minimum,1e-9); n=max(len(values)-1,1)
    return " ".join(f"{left+i*(width/n):.2f},{top+height-(v-minimum)*(height/span):.2f}" for i,v in enumerate(values))


def svg_plot(path: Path, trace: str, mutation_id: str, target_s: list[int], base: list[float], mutated: list[float], support: set[int], oracle_policy: list[dict], forecast_policy: list[dict]) -> None:
    width,height,left=1200,700,75; chart_w=1080
    residual=[m-b for b,m in zip(base,mutated)]; oracle_rep=[int(x["commanded_replicas"]) for x in oracle_policy]; mut_rep=[int(x["commanded_replicas"]) for x in forecast_policy]
    changed=[i for i,t in enumerate(target_s) if t in support]
    shade=""
    if changed:
        x1=left+min(changed)*chart_w/max(len(base)-1,1);x2=left+(max(changed)+1)*chart_w/max(len(base)-1,1)
        shade=f'<rect x="{x1:.2f}" y="55" width="{max(x2-x1,1):.2f}" height="560" fill="#f59e0b" opacity="0.12"/>'
    def poly(vals,top,h,lo,hi,color): return f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{points(vals,chart_w,h,left,top,lo,hi)}"/>'
    body=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="white"/><text x="{left}" y="28" font-family="sans-serif" font-size="18">{trace}: {mutation_id}</text>{shade}
<line x1="{left}" y1="260" x2="1155" y2="260" stroke="#ddd"/><line x1="{left}" y1="455" x2="1155" y2="455" stroke="#ddd"/>
<text x="8" y="85" font-family="sans-serif" font-size="13">RPS</text><text x="8" y="320" font-family="sans-serif" font-size="13">residual</text><text x="8" y="520" font-family="sans-serif" font-size="13">replicas</text>
{poly(base,55,180,0,65,'#2563eb')}{poly(mutated,55,180,0,65,'#dc2626')}
{poly(residual,285,130,-40,40,'#7c3aed')}
{poly(oracle_rep,485,130,0,4,'#2563eb')}{poly(mut_rep,485,130,0,4,'#dc2626')}
<text x="780" y="48" font-family="sans-serif" font-size="12" fill="#2563eb">oracle/actual</text><text x="900" y="48" font-family="sans-serif" font-size="12" fill="#dc2626">mutated forecast</text>
<text x="{left}" y="660" font-family="sans-serif" font-size="12">target time {target_s[0]}..{target_s[-1]} s; orange = declared mutation support; residual = forecast - oracle</text></svg>'''
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(body,encoding="utf-8",newline="\n")


def png_plot(path: Path, trace: str, mutation_id: str, target_s: list[int], base: list[float], mutated: list[float], support: set[int], oracle_policy: list[dict], forecast_policy: list[dict]) -> None:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return
    image=Image.new("RGB",(1200,700),"white");draw=ImageDraw.Draw(image);left,right=75,1155;chart_w=right-left
    draw.text((left,12),f"{trace}: {mutation_id}",fill="black")
    changed=[i for i,t in enumerate(target_s) if t in support]
    if changed:
        x1=left+min(changed)*chart_w/max(len(base)-1,1);x2=left+(max(changed)+1)*chart_w/max(len(base)-1,1)
        draw.rectangle((x1,45,x2,620),fill=(255,245,220))
    for y in (260,455,620):draw.line((left,y,right,y),fill=(210,210,210),width=1)
    def line(vals,top,height,low,high,color):
        span=max(high-low,1e-9);pts=[(left+i*chart_w/max(len(vals)-1,1),top+height-(v-low)*height/span) for i,v in enumerate(vals)];draw.line(pts,fill=color,width=2)
    residual=[m-b for b,m in zip(base,mutated)];oracle=[int(x["commanded_replicas"]) for x in oracle_policy];forecast=[int(x["commanded_replicas"]) for x in forecast_policy]
    line(base,55,180,0,65,(37,99,235));line(mutated,55,180,0,65,(220,38,38));line(residual,285,130,-40,40,(124,58,237));line(oracle,485,130,0,4,(37,99,235));line(forecast,485,130,0,4,(220,38,38))
    draw.text((10,80),"RPS",fill="black");draw.text((10,320),"residual",fill="black");draw.text((10,520),"replicas",fill="black")
    draw.text((left,650),f"target {target_s[0]}..{target_s[-1]} s; orange=support; blue=oracle; red=mutated",fill="black")
    path.parent.mkdir(parents=True,exist_ok=True);image.save(path)


def generate_one(spec: dict, step7: Path, policy: Policy, policy_hash: str, output: Path, catalog: dict) -> dict:
    trace=spec["trace"]; workload_path=step7/"workloads"/f"{trace}.csv"; annotation_path=step7/"annotations"/f"{trace}.annotations.json"
    workload, workload_rows=load_workload(workload_path); targets, base=oracle_forecast(workload,policy.horizon_s)
    base_map=dict(zip(targets,base)); mutated_map,support=mutate(base_map,spec,*map(float,catalog["validated_rps_range"]))
    mutated=[mutated_map[t] for t in targets]; changed={t for t,b,m in zip(targets,base,mutated) if abs(b-m)>1e-9}
    if not changed: raise ValueError(f"mutation has no effect: {spec['id']}")
    if not changed <= support: raise ValueError(f"mutation changed values outside declared support: {spec['id']}")
    oracle_policy=policy.replay(base); forecast_policy=policy.replay(mutated); metric=metrics(base,mutated,targets,support,oracle_policy,forecast_policy)
    mutation_id=spec["id"]; condition=spec["label"]
    support_residual=[m-b for t,b,m in zip(targets,base,mutated) if t in support]
    metric["affected_peak_residual_rps"]=round(max(support_residual,key=abs),6)
    metric["event_presence_error"]="missed_peak" if condition=="missed_peak" else ("false_peak" if condition=="false_peak" else "none")
    if condition=="missed_peak": metric["peak_timing_error_s"]=None
    forecast_rows=[]
    for issued,(target,value) in enumerate(zip(targets,mutated)):
        forecast_rows.append({"trace_id":trace,"condition":condition,"issued_offset_ms":issued*1000,
                              "target_offset_ms":target*1000,"horizon_ms":policy.horizon_s*1000,
                              "predicted_rps":f"{value:.6f}","mutation_id":mutation_id,
                              "pair_manifest_id":catalog["pair_manifest_id"]})
    forecast_path=output/"forecasts"/trace/f"{mutation_id}.forecast.csv";write_csv(forecast_path,forecast_rows)
    decision_rows=[]
    for oracle,forecast in zip(oracle_policy,forecast_policy):
        decision_rows.append({"trace_id":trace,"mutation_id":mutation_id,"decision_seq":forecast["decision_seq"],
                              "decision_offset_ms":forecast["decision_offset_ms"],"forecast_target_offset_ms":targets[forecast["decision_seq"]]*1000,
                              "oracle_rps":oracle["predicted_rps"],"forecast_rps":forecast["predicted_rps"],
                              "oracle_raw_replicas":oracle["raw_replicas"],"forecast_raw_replicas":forecast["raw_replicas"],
                              "oracle_commanded_replicas":oracle["commanded_replicas"],"forecast_commanded_replicas":forecast["commanded_replicas"],
                              "forecast_action":forecast["action"],"forecast_scale_down_held":forecast["scale_down_held"]})
    replica_path=output/"replica-timelines"/trace/f"{mutation_id}.replicas.csv";write_csv(replica_path,decision_rows)
    metadata={"schema_version":VERSION,"generator_version":VERSION,"mutation_id":mutation_id,"source_workload":trace,
              "source_suite_version":workload_rows[0]["suite_version"],"mutation_family":spec["family"],"mutation_type":spec["type"],
              "semantic_label":condition,"parameters":spec["parameters"],"forecast_horizon_seconds":policy.horizon_s,
              "affected_target_intervals_s":intervals(support & set(targets)),"changed_target_intervals_s":intervals(changed),
              "affected_issue_intervals_s":intervals(t-policy.horizon_s for t in support & set(targets)),
              "changed_issue_intervals_s":intervals(t-policy.horizon_s for t in changed),"metrics":metric,
              "input_sha256":sha256(workload_path),"annotation_sha256":sha256(annotation_path),"forecast_sha256":sha256(forecast_path),
              "replica_timeline_sha256":sha256(replica_path),"policy_id":policy.policy_id,"policy_sha256":policy_hash,
              "outside_support_unchanged":all(abs(b-m)<=1e-9 for t,b,m in zip(targets,base,mutated) if t not in support)}
    metadata_path=output/"metadata"/trace/f"{mutation_id}.json";write_json(metadata_path,metadata)
    svg_plot(output/"plots"/trace/f"{mutation_id}.svg",trace,mutation_id,targets,base,mutated,support,oracle_policy,forecast_policy)
    png_plot(output/"plots"/trace/f"{mutation_id}.png",trace,mutation_id,targets,base,mutated,support,oracle_policy,forecast_policy)
    return {"mutation_id":mutation_id,"trace_id":trace,"family":spec["family"],"type":spec["type"],"label":condition,
            **metric,"forecast_path":str(forecast_path.relative_to(output)),"metadata_path":str(metadata_path.relative_to(output)),
            "replica_path":str(replica_path.relative_to(output)),"plot_path":str((output/"plots"/trace/f"{mutation_id}.svg").relative_to(output))}


def generate_all(step7: Path, policy_path: Path, catalog_path: Path, output: Path) -> list[dict]:
    catalog=json.loads(catalog_path.read_text(encoding="utf-8-sig"));policy=Policy.load(policy_path)
    if policy.horizon_s != int(catalog["forecast_horizon_seconds"]): raise ValueError("catalog/policy horizon mismatch")
    policy_hash=sha256(policy_path); seen=set(); results=[]
    for trace in sorted({spec["trace"] for spec in catalog["mutations"]}):
        workload,_=load_workload(step7/"workloads"/f"{trace}.csv");targets,base=oracle_forecast(workload,policy.horizon_s)
        rows=[{"trace_id":trace,"condition":"oracle","issued_offset_ms":i*1000,"target_offset_ms":target*1000,
               "horizon_ms":policy.horizon_s*1000,"predicted_rps":f"{value:.6f}","mutation_id":"oracle-reference-v1",
               "pair_manifest_id":catalog["pair_manifest_id"]} for i,(target,value) in enumerate(zip(targets,base))]
        write_csv(output/"base-forecasts"/f"{trace}.oracle-forecast.csv",rows)
    for spec in catalog["mutations"]:
        if spec["id"] in seen: raise ValueError(f"duplicate mutation id {spec['id']}")
        seen.add(spec["id"]);results.append(generate_one(spec,step7,policy,policy_hash,output,catalog))
    write_csv(output/"metrics"/"mutation-metrics.csv",results)
    write_json(output/"manifests"/"catalog.json",{"schema_version":VERSION,"generator_version":VERSION,
               "candidate_count":len(results),"source_catalog_sha256":sha256(catalog_path),"policy_sha256":sha256(policy_path),"candidates":results})
    return results
