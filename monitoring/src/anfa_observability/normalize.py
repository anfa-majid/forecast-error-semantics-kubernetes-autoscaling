from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean

from .common import parse_utc


def jsonl(path: str | Path) -> list[dict]:
    values=[]
    with Path(path).open(encoding="utf-8-sig") as handle:
        for line in handle:
            try:
                item=json.loads(line)
                if isinstance(item,dict): values.append(item)
            except json.JSONDecodeError:
                continue
    return values


def percentile(values: list[float], fraction: float) -> float | None:
    if not values: return None
    ordered=sorted(values); index=(len(ordered)-1)*fraction; lower=math.floor(index); upper=math.ceil(index)
    if lower==upper: return ordered[lower]
    return ordered[lower]*(upper-index)+ordered[upper]*(index-lower)


def aggregate_requests(records: list[dict]) -> dict[int,dict]:
    result=defaultdict(lambda:{"dispatched_requests":0,"completed_requests":0,"successful_requests":0,"failed_requests":0,"timeouts":0,"latency_ms":[],"dispatch_lateness_ms":[],"serving_pods":set()})
    for record in records:
        dispatch=int(record["dispatch_offset_us"]//1_000_000); completion=int(record["completion_offset_us"]//1_000_000)
        result[dispatch]["dispatched_requests"]+=1; result[dispatch]["dispatch_lateness_ms"].append(record["dispatch_lateness_us"]/1000)
        result[completion]["completed_requests"]+=1; result[completion]["latency_ms"].append(record["latency_us"]/1000)
        if record.get("success"): result[completion]["successful_requests"]+=1
        else: result[completion]["failed_requests"]+=1
        if record.get("timeout"): result[completion]["timeouts"]+=1
        if record.get("pod_name"): result[completion]["serving_pods"].add(record["pod_name"])
    return result


def load_workload(path: str | Path) -> dict[int,dict]:
    with Path(path).open(newline="",encoding="utf-8-sig") as handle:
        return {int(row["offset_ms"])//1000:row for row in csv.DictReader(handle)}


def load_controller(path: str | Path) -> dict[int,dict]:
    return {int(row["tick_offset_ms"])//1000:row for row in jsonl(path) if row.get("record_type")=="decision"}


def load_kubernetes(path: str | Path,t0_utc:str) -> dict[int,dict]:
    t0_ns=int(parse_utc(t0_utc).timestamp()*1e9); grouped=defaultdict(list)
    for row in jsonl(path):
        second=int((row["observed_epoch_ns"]-t0_ns)//1_000_000_000)
        if second>=0: grouped[second].append(row)
    return {second:max(items,key=lambda row:row["observed_epoch_ns"]) for second,items in grouped.items()}


def prometheus_samples(directory: str | Path,t0_utc:str) -> dict[str,dict[int,list[tuple[dict,float]]]]:
    t0=parse_utc(t0_utc).timestamp(); result={}
    for path in Path(directory).glob("*.json"):
        if path.name=="export-summary.json": continue
        value=json.loads(path.read_text(encoding="utf-8")); query_id=value.get("query_id",path.stem); by_second=defaultdict(list)
        for series in value.get("response",{}).get("data",{}).get("result",[]):
            labels=series.get("metric",{})
            for timestamp,sample in series.get("values",[]):
                try: by_second[int(round(float(timestamp)-t0))].append((labels,float(sample)))
                except (TypeError,ValueError): continue
        result[query_id]=by_second
    return result


def scalar_sum(data:dict[str,dict],query:str,second:int) -> float|None:
    samples=data.get(query,{}).get(second,[])
    return sum(value for _,value in samples) if samples else None


def write_csv(path: str|Path, rows:list[dict]) -> None:
    destination=Path(path);destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def build_timeline(*,workload_path:str,requests_path:str,controller_path:str,kubernetes_path:str,
                   prometheus_directory:str,t0_utc:str,duration_seconds:int,output_path:str) -> list[dict]:
    workload=load_workload(workload_path); requests=aggregate_requests(jsonl(requests_path)); controller=load_controller(controller_path)
    kubernetes=load_kubernetes(kubernetes_path,t0_utc); prometheus=prometheus_samples(prometheus_directory,t0_utc)
    rows=[]; last_kube=None
    for second in range(duration_seconds):
        req=requests.get(second,{}); ctl=controller.get(second); current_kube=kubernetes.get(second)
        if current_kube: last_kube=current_kube
        dep=(last_kube or {}).get("deployment",{}); pods=(last_kube or {}).get("pods",[]); endpoints=(last_kube or {}).get("endpoints",[])
        latencies=req.get("latency_ms",[]); lateness=req.get("dispatch_lateness_ms",[]); work=workload.get(second,{})
        rows.append({
            "second":second,"offset_ms":second*1000,"target_rps":work.get("target_rps"),"workload_phase":work.get("phase",""),"workload_event":work.get("event_label",""),
            "offered_requests":work.get("scheduled_requests_in_second",work.get("target_rps")),
            "dispatched_requests":req.get("dispatched_requests",0),"completed_requests":req.get("completed_requests",0),"successful_requests":req.get("successful_requests",0),
            "failed_requests":req.get("failed_requests",0),"timeouts":req.get("timeouts",0),"latency_p50_ms":percentile(latencies,.5),"latency_p95_ms":percentile(latencies,.95),"latency_p99_ms":percentile(latencies,.99),
            "dispatch_lateness_p99_ms":percentile(lateness,.99),"observed_serving_pods":len(req.get("serving_pods",set())),
            "forecast_rps":ctl.get("predicted_rps") if ctl else None,"oracle_replicas":work.get("oracle_replicas"),"raw_replicas":ctl.get("raw_replicas") if ctl else None,
            "bounded_replicas":ctl.get("bounded_replicas") if ctl else None,"stabilized_replicas":ctl.get("stabilized_replicas") if ctl else None,
            "commanded_replicas":ctl.get("commanded_replicas") if ctl else None,"controller_action":ctl.get("action","") if ctl else "","scale_down_held":ctl.get("scale_down_held") if ctl else None,
            "safety_net_enabled":False,"safety_net_state":"not_applicable",
            "deployment_desired_replicas":dep.get("desired_replicas"),"deployment_current_replicas":dep.get("current_replicas"),"deployment_ready_replicas":dep.get("ready_replicas"),"deployment_available_replicas":dep.get("available_replicas"),
            "pod_ready_count":sum(bool(p.get("ready")) for p in pods),"service_ready_endpoints":sum(e.get("ready") is True and e.get("serving") is not False for e in endpoints),
            "pod_restart_count":sum(int(p.get("restart_count",0)) for p in pods),"pod_cpu_cores":scalar_sum(prometheus,"pod_cpu",second),"pod_memory_bytes":scalar_sum(prometheus,"pod_memory",second),
            "cpu_throttling_ratio":scalar_sum(prometheus,"cpu_throttling_ratio",second),"network_receive_bytes_s":scalar_sum(prometheus,"network_receive",second),"network_transmit_bytes_s":scalar_sum(prometheus,"network_transmit",second),
            "application_requests_s":scalar_sum(prometheus,"application_requests",second),"application_errors_s":scalar_sum(prometheus,"application_errors",second),
            "controller_present":ctl is not None,"kubernetes_present":current_kube is not None,"prometheus_present":any(second in values for values in prometheus.values()),
        })
    write_csv(output_path,rows);return rows


def main()->None:
    parser=argparse.ArgumentParser(description="Build the ANFA second-by-second causal timeline")
    for item in ("workload-path","requests-path","controller-path","kubernetes-path","prometheus-directory","t0-utc","output-path"):parser.add_argument("--"+item,required=True)
    parser.add_argument("--duration-seconds",required=True,type=int);args=parser.parse_args()
    rows=build_timeline(**vars(args));print(json.dumps({"rows":len(rows),"output":args.output_path},indent=2))


if __name__=="__main__":main()
