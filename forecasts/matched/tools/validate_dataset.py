from __future__ import annotations
import argparse,csv,json,math,sys,tempfile
from pathlib import Path
from matching_framework import generate_candidates,match,rel_diff,load_step11

def rows(path):
    with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def validate(root:Path,step7:Path,step8_policy:Path,step11:Path)->dict:
    m=load_step11(step11);checks=[]
    def add(name,passed,details=""):checks.append({"name":name,"passed":bool(passed),"details":details})
    protocol_path=root/"configuration/matching-protocol.json";protocol=json.loads(protocol_path.read_text(encoding="utf-8-sig"))
    dataset=json.loads((root/"manifests/matched-dataset.json").read_text(encoding="utf-8-sig"));pairs=dataset["pairs"]
    add("protocol_preregistered",protocol.get("status")=="preregistered-before-live-operational-comparison")
    add("protocol_hash_frozen",dataset.get("protocol_sha256")==m.sha256(protocol_path))
    add("seven_contrast_groups",len(pairs)==7 and len({x["contrast_group"] for x in pairs})==7,f"pairs={len(pairs)}")
    add("same_workload_within_pairs",all(x["forecast_a"]["trace_id"]==x["forecast_b"]["trace_id"]==x["trace_id"] for x in pairs))
    add("all_matching_tolerances",all(x["matching"]["mae_relative_difference"]<=protocol["mae_relative_tolerance"] and x["matching"]["rmse_relative_difference"]<=protocol["rmse_relative_tolerance"] for x in pairs))
    add("semantic_gates_pass",all(x["semantic_validation"]["passed"] for x in pairs))
    ids=[z["candidate_id"] for x in pairs for z in (x["forecast_a"],x["forecast_b"])]
    add("no_primary_candidate_reuse",len(ids)==len(set(ids)),f"candidate_uses={len(ids)}")
    add("outcome_blind_provenance",all(x["selection_provenance"]["outcome_blind"] and x["selection_provenance"]["forbidden_fields_not_used"]==protocol["forbidden_selection_fields"] for x in pairs))
    candidate_metrics=rows(root/"metrics/candidate-metrics.csv");columns=set(candidate_metrics[0]);forbidden=set(protocol["forbidden_selection_fields"])
    add("selector_table_excludes_operational_fields",not(columns&forbidden),f"intersection={sorted(columns&forbidden)}")
    recompute_errors=[];contract_errors=[];copy_errors=[]
    for pair in pairs:
        workload,_=m.load_workload(step7/"workloads"/f"{pair['trace_id']}.csv");targets,base=m.oracle_forecast(workload,6)
        for label,key in (("a","forecast_a"),("b","forecast_b")):
            candidate=pair[key];source=root/candidate["forecast_path"];accepted=root/"accepted-pairs"/pair["pair_id"]/f"forecast-{label}.csv"
            if m.sha256(source)!=m.sha256(accepted):copy_errors.append(pair["pair_id"]+":"+label)
            data=rows(accepted);issued=[int(x["issued_offset_ms"]) for x in data]
            if issued!=list(range(0,len(data)*1000,1000)) or any(int(x["target_offset_ms"])-int(x["issued_offset_ms"])!=6000 or int(x["horizon_ms"])!=6000 for x in data):contract_errors.append(pair["pair_id"]+":"+label)
            values=[float(x["predicted_rps"]) for x in data];residual=[x-y for x,y in zip(values,base)];mae=sum(map(abs,residual))/len(residual);rmse=math.sqrt(sum(x*x for x in residual)/len(residual))
            if abs(mae-pair["matching"][f"mae_{label}_rps"])>1e-9 or abs(rmse-pair["matching"][f"rmse_{label}_rps"])>1e-9:recompute_errors.append(pair["pair_id"]+":"+label)
        if rel_diff(pair["matching"]["mae_a_rps"],pair["matching"]["mae_b_rps"])>protocol["mae_relative_tolerance"]:recompute_errors.append(pair["pair_id"]+":mae")
    add("accepted_forecasts_exact_candidate_copies",not copy_errors,f"errors={copy_errors}")
    add("accepted_forecast_contract",not contract_errors,f"errors={contract_errors}")
    add("accuracy_metrics_independently_recomputed",not recompute_errors,f"errors={recompute_errors}")
    distances=rows(root/"metrics/pair-distance-table.csv");rejections=rows(root/"rejected-pairs/rejection-ledger.csv")
    add("complete_pair_search_ledger",len(distances)>len(pairs),f"comparisons={len(distances)}")
    add("explicit_rejection_reasons",bool(rejections) and all(x["rejection_reasons"] not in ("","[]") for x in rejections),f"rejections={len(rejections)}")
    plots=list((root/"plots").glob("*.png"));add("pair_plots_complete",len(plots)==len(pairs) and all(x.stat().st_size>1000 for x in plots),f"plots={len(plots)}")
    with tempfile.TemporaryDirectory() as directory:
        temp=Path(directory)
        # Copy only frozen configuration; generated outputs must not depend on documentation or prior artifacts.
        (temp/"configuration").mkdir(parents=True); 
        for name in ("matching-protocol.json","parameter-grids.json","semantic-constraints.json"):(temp/"configuration"/name).write_bytes((root/"configuration"/name).read_bytes())
        candidates=generate_candidates(temp,step7,step11,temp/"configuration/parameter-grids.json");match(temp,step7,step8_policy,step11,temp/"configuration/matching-protocol.json",candidates)
        compare_roots=("candidates","candidate-metadata","accepted-pairs","metrics","rejected-pairs","plots","manifests")
        mismatches=[];checked=0
        for folder in compare_roots:
            for generated in (temp/folder).rglob("*"):
                if generated.is_file():
                    checked+=1;expected=root/generated.relative_to(temp)
                    if not expected.exists() or m.sha256(generated)!=m.sha256(expected):mismatches.append(str(generated.relative_to(temp)))
        add("byte_exact_regeneration",not mismatches,f"checked={checked}, mismatches={mismatches}")
    valid=all(x["passed"] for x in checks);result={"schema_version":"1.0.0","valid":valid,"pair_count":len(pairs),"checks":checks}
    m.write_json(root/"validation/validation-summary.json",result);return result

def main():
    p=argparse.ArgumentParser();p.add_argument("--root",required=True);p.add_argument("--step7-root",required=True);p.add_argument("--step8-policy",required=True);p.add_argument("--step11-root",required=True)
    a=p.parse_args();result=validate(Path(a.root),Path(a.step7_root),Path(a.step8_policy),Path(a.step11_root));print(json.dumps(result,indent=2));raise SystemExit(0 if result["valid"] else 1)
if __name__=="__main__":main()
