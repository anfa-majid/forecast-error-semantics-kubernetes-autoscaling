from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .common import iso_utc, parse_utc, sha256_file, write_json
from .normalize import jsonl


REQUIRED_METADATA=("schema_version","experiment_id","run_id","workload_id","forecast_condition","controller_version","controller_image","application_image","cluster_version","random_seed","t0_utc","started_utc","ended_utc","status")


def check_run(run_directory:str|Path,maximum_clock_skew_ms:float=100,maximum_dispatch_lateness_ms:float=100,metric_catalog:str|Path|None=None)->dict:
    root=Path(run_directory);checks=[]
    def add(name,passed,details="",severity="error"):checks.append({"name":name,"passed":bool(passed),"severity":severity,"details":details})
    metadata_path=root/"metadata/run-metadata.json"
    metadata=json.loads(metadata_path.read_text(encoding="utf-8-sig")) if metadata_path.exists() else {}
    missing=[name for name in REQUIRED_METADATA if name not in metadata];add("required_metadata",not missing,f"missing={missing}")
    clock_path=root/"metadata/clock-preflight.json";clock=json.loads(clock_path.read_text(encoding="utf-8-sig")) if clock_path.exists() else {}
    skew=clock.get("maximum_absolute_skew_ms");add("clock_skew",skew is not None and skew<=maximum_clock_skew_ms,f"observed={skew}, limit={maximum_clock_skew_ms}")
    if clock.get("mode")=="measured_offset_correction":
        add("clock_offset_correction",clock.get("passed") and clock.get("maximum_corrected_residual_ms",float("inf"))<=maximum_clock_skew_ms,f"correction_ms={clock.get('runner_correction_ms')}, residual_ms={clock.get('maximum_corrected_residual_ms')}")
        checks[-2]["severity"]="information"
    post_path=root/"metadata/clock-postflight.json";post=json.loads(post_path.read_text(encoding="utf-8-sig")) if post_path.exists() else {}
    if clock.get("mode")=="measured_offset_correction":
        drift=abs(float(post.get("runner_correction_ms",float("inf")))-float(clock.get("runner_correction_ms",0)))
        add("clock_correction_drift",post.get("passed") and drift<=maximum_clock_skew_ms,f"drift_ms={drift}")
    request_path=root/"raw/load-generator-requests.jsonl";requests=jsonl(request_path) if request_path.exists() else []
    add("request_records_present",bool(requests),f"records={len(requests)}")
    if requests:
        ids=[row.get("request_id") for row in requests];add("request_ids_unique",len(ids)==len(set(ids)))
        lateness=max(row.get("dispatch_lateness_us",0) for row in requests)/1000;add("dispatch_lateness",lateness<=maximum_dispatch_lateness_ms,f"maximum_ms={lateness}")
    controller_path=root/"raw/controller.jsonl";decisions=[r for r in jsonl(controller_path) if r.get("record_type")=="decision"] if controller_path.exists() else []
    add("controller_decisions_present",bool(decisions),f"decisions={len(decisions)}")
    if decisions:
        sequences=[r["decision_seq"] for r in decisions];add("controller_sequence",sequences==list(range(len(sequences))),f"first={sequences[0]}, last={sequences[-1]}")
        add("controller_api_errors",not any(r.get("api_result")=="error" for r in decisions))
        add("policy_hash_constant",len({r.get("policy_config_sha256") for r in decisions})==1)
        add("forecast_hash_constant",len({r.get("forecast_sha256") for r in decisions})==1)
        if metadata.get("t0_utc"):
            t0=parse_utc(metadata["t0_utc"])
            timing_errors=[abs((parse_utc(r["timestamp_utc"])-t0).total_seconds()*1000-r["tick_offset_ms"]) for r in decisions]
            add("controller_decision_timing",max(timing_errors)<=250,f"maximum_absolute_lag_ms={max(timing_errors):.3f}, limit=250")
            timestamps=[parse_utc(r["timestamp_utc"]) for r in decisions]
            catchup=sum((timestamps[i]-timestamps[i-1]).total_seconds()<.5 for i in range(1,len(timestamps)))
            add("controller_no_catchup_burst",catchup==0,f"sub_500ms_intervals={catchup}")
    kube_path=root/"raw/kubernetes-snapshots.jsonl";snapshots=jsonl(kube_path) if kube_path.exists() else []
    add("kubernetes_snapshots_present",bool(snapshots),f"snapshots={len(snapshots)}")
    add("kubernetes_collection_errors",not any(r.get("collection_error") for r in snapshots),f"errors={sum(bool(r.get('collection_error')) for r in snapshots)}")
    prometheus_summary=root/"raw/prometheus/export-summary.json";prometheus=json.loads(prometheus_summary.read_text(encoding="utf-8-sig")) if prometheus_summary.exists() else {}
    add("prometheus_export_present",bool(prometheus));add("prometheus_query_errors",bool(prometheus) and not prometheus.get("errors"),str(prometheus.get("errors",{})))
    catalog_path=Path(metric_catalog) if metric_catalog else Path(__file__).resolve().parents[2]/"configuration/metric-catalog.json"
    catalog=json.loads(catalog_path.read_text(encoding="utf-8-sig")) if catalog_path.exists() else {}
    required_prometheus=sorted({item["query_id"] for item in catalog.get("metrics",[]) if item.get("source")=="prometheus" and item.get("required")})
    query_results=prometheus.get("queries",{})
    missing_series=[query_id for query_id in required_prometheus if int(query_results.get(query_id,{}).get("samples",0))==0]
    add("required_prometheus_series",bool(required_prometheus) and not missing_series,f"required={required_prometheus}, zero_sample={missing_series}")
    timeline_path=root/"normalized/joined-timeline.csv"
    timeline=list(csv.DictReader(timeline_path.open(encoding="utf-8-sig"))) if timeline_path.exists() else []
    add("joined_timeline_present",bool(timeline),f"rows={len(timeline)}")
    if timeline:
        seconds=[int(row["second"]) for row in timeline];add("joined_timeline_sequence",seconds==list(range(len(seconds))))
        missing_controller=sum(row["controller_present"].lower()!="true" for row in timeline);add("controller_timeline_coverage",missing_controller==0,f"missing_seconds={missing_controller}")
        missing_kube=sum(row["kubernetes_present"].lower()!="true" for row in timeline);add("kubernetes_timeline_coverage",missing_kube==0,f"missing_seconds={missing_kube}")
        missing_prom=sum(row["prometheus_present"].lower()!="true" for row in timeline);add("prometheus_timeline_coverage",missing_prom==0,f"missing_seconds={missing_prom}")
    required_files=[metadata_path,clock_path,request_path,controller_path,kube_path,prometheus_summary,timeline_path]
    add("required_files",all(path.exists() for path in required_files),f"missing={[str(p.relative_to(root)) for p in required_files if not p.exists()]}")
    valid=all(item["passed"] for item in checks if item["severity"]=="error")
    report={"schema_version":"1.0.0","validated_utc":iso_utc(),"run_directory":str(root),"valid":valid,"checks":checks,"file_hashes":{str(path.relative_to(root)):sha256_file(path) for path in required_files if path.exists()}}
    write_json(root/"validation/completeness-report.json",report);return report


def main()->None:
    parser=argparse.ArgumentParser(description="Validate completeness and causal reconstructability of an ANFA run")
    parser.add_argument("run_directory");parser.add_argument("--maximum-clock-skew-ms",type=float,default=100);parser.add_argument("--maximum-dispatch-lateness-ms",type=float,default=100);parser.add_argument("--metric-catalog")
    args=parser.parse_args();report=check_run(args.run_directory,args.maximum_clock_skew_ms,args.maximum_dispatch_lateness_ms,args.metric_catalog);print(json.dumps(report,indent=2));raise SystemExit(0 if report["valid"] else 1)


if __name__=="__main__":main()
