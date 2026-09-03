from __future__ import annotations
import argparse, csv, json, tempfile
from pathlib import Path
from mutation_framework import generate_all, read_csv, sha256, write_json

REQUIRED_LABELS={"early_event","late_event","missed_peak","false_peak","underprediction","overprediction",
                 "persistent_negative_bias","persistent_positive_bias","short_error","shortened_peak","extended_peak",
                 "smoothed_peak","exaggerated_peak","slope_reduction","slope_exaggeration","stable_period_error","transition_period_error"}

def validate(root:Path,step7:Path,step8:Path,policy:Path,catalog_path:Path)->dict:
    checks=[]
    def add(name,passed,details=""): checks.append({"name":name,"passed":bool(passed),"details":details})
    catalog=json.loads(catalog_path.read_text(encoding="utf-8-sig"));specs=catalog["mutations"]
    labels={x["label"] for x in specs};ids=[x["id"] for x in specs]
    add("required_semantics_present",REQUIRED_LABELS<=labels,f"missing={sorted(REQUIRED_LABELS-labels)}")
    add("mutation_ids_unique",len(ids)==len(set(ids)),f"count={len(ids)}")
    add("all_workloads_represented",{x["trace"] for x in specs}=={"gradual-ramp-v1","narrow-spike-v1","sustained-peak-v1","periodic-triangle-v1","stable-noisy-control-v1"})
    metrics=read_csv(root/"metrics"/"mutation-metrics.csv")
    add("metric_rows_complete",len(metrics)==len(specs),f"metrics={len(metrics)}, specs={len(specs)}")
    metadata=[]
    for spec in specs:
        path=root/"metadata"/spec["trace"]/f"{spec['id']}.json"
        if path.exists(): metadata.append(json.loads(path.read_text(encoding="utf-8-sig")))
    add("metadata_complete",len(metadata)==len(specs),f"metadata={len(metadata)}")
    add("outside_support_unchanged",all(x.get("outside_support_unchanged") for x in metadata))
    add("parameters_saved",all(x.get("parameters") for x in metadata))
    add("affected_intervals_saved",all(x.get("affected_target_intervals_s") and x.get("changed_target_intervals_s") for x in metadata))
    add("metrics_saved",all(x.get("metrics") for x in metadata))
    range_errors=[];contract_errors=[];hash_errors=[]
    required_columns=["trace_id","condition","issued_offset_ms","target_offset_ms","horizon_ms","predicted_rps","mutation_id","pair_manifest_id"]
    for spec in specs:
        forecast=root/"forecasts"/spec["trace"]/f"{spec['id']}.forecast.csv";rows=read_csv(forecast)
        if list(rows[0])!=required_columns:contract_errors.append(spec["id"]+":columns")
        offsets=[int(x["issued_offset_ms"]) for x in rows]
        if offsets!=list(range(0,len(rows)*1000,1000)):contract_errors.append(spec["id"]+":offsets")
        if any(int(x["horizon_ms"])!=6000 or int(x["target_offset_ms"])-int(x["issued_offset_ms"])!=6000 for x in rows):contract_errors.append(spec["id"]+":horizon")
        if any(not 0<=float(x["predicted_rps"])<=65 for x in rows):range_errors.append(spec["id"])
        meta=next(x for x in metadata if x["mutation_id"]==spec["id"])
        if sha256(forecast)!=meta["forecast_sha256"]:hash_errors.append(spec["id"]+":forecast")
        replica=root/"replica-timelines"/spec["trace"]/f"{spec['id']}.replicas.csv"
        if sha256(replica)!=meta["replica_timeline_sha256"]:hash_errors.append(spec["id"]+":replica")
    add("forecast_contract",not contract_errors,f"errors={contract_errors}")
    add("forecast_values_in_validated_range",not range_errors,f"errors={range_errors}")
    add("artifact_hashes_match_metadata",not hash_errors,f"errors={hash_errors}")
    oracle_errors=[]
    for trace in sorted({x["trace"] for x in specs}):
        candidate=next(x for x in specs if x["trace"]==trace)
        generated=read_csv(root/"replica-timelines"/trace/f"{candidate['id']}.replicas.csv")
        authoritative=read_csv(step8/"timelines"/f"{trace}.oracle-decisions.csv")
        if len(generated)!=len(authoritative):oracle_errors.append(trace+":length");continue
        for g,a in zip(generated,authoritative):
            if (int(g["oracle_raw_replicas"]),int(g["oracle_commanded_replicas"]))!=(int(a["raw_replicas"]),int(a["commanded_replicas"])):
                oracle_errors.append(trace+f":decision-{g['decision_seq']}");break
    add("oracle_policy_exact_step8",not oracle_errors,f"errors={oracle_errors}")
    plots=[p for p in (root/"plots").rglob("*.svg")]
    add("plots_complete",len(plots)==len(specs) and all(p.stat().st_size>1000 for p in plots),f"plots={len(plots)}")
    with tempfile.TemporaryDirectory() as directory:
        temp=Path(directory);generate_all(step7,policy,catalog_path,temp)
        generated_files=sorted(p.relative_to(temp) for p in temp.rglob("*") if p.is_file())
        mismatches=[]
        for relative in generated_files:
            expected=root/relative
            if not expected.exists() or sha256(temp/relative)!=sha256(expected):mismatches.append(str(relative))
        add("byte_exact_regeneration",not mismatches,f"checked={len(generated_files)}, mismatches={mismatches}")
    valid=all(x["passed"] for x in checks)
    result={"schema_version":"1.0.0","valid":valid,"candidate_count":len(specs),"checks":checks}
    write_json(root/"validation"/"validation-summary.json",result);return result

def main():
    p=argparse.ArgumentParser();p.add_argument("--root",required=True);p.add_argument("--step7-root",required=True);p.add_argument("--step8-root",required=True);p.add_argument("--policy",required=True);p.add_argument("--catalog",required=True)
    a=p.parse_args();result=validate(Path(a.root),Path(a.step7_root),Path(a.step8_root),Path(a.policy),Path(a.catalog));print(json.dumps(result,indent=2));raise SystemExit(0 if result["valid"] else 1)
if __name__=="__main__":main()
