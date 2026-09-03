from __future__ import annotations
import csv, hashlib, json, math, sys
from pathlib import Path


def load_step11(step11_root:Path):
    sys.path.insert(0,str(step11_root/"tools"))
    import mutation_framework as m
    return m


def rel_diff(a:float,b:float)->float:
    denominator=abs(a)+abs(b)
    return 0.0 if denominator==0 else 2*abs(a-b)/denominator


def metric(base:list[float],values:list[float],targets:list[int],support:set[int],label:str)->dict:
    residual=[v-b for b,v in zip(base,values)];n=len(base);region=[i for i,t in enumerate(targets) if t in support]
    peak_base=max(base);peak=max(values);threshold=(min(base)+max(base))/2
    timing=None if label=="missed_peak" else targets[values.index(peak)]-targets[base.index(peak_base)]
    return {"mae_rps":sum(abs(x) for x in residual)/n,"rmse_rps":math.sqrt(sum(x*x for x in residual)/n),
            "signed_bias_rps":sum(residual)/n,"maximum_absolute_error_rps":max(abs(x) for x in residual),
            "region_mae_rps":sum(abs(residual[i]) for i in region)/len(region),"changed_decisions":sum(abs(x)>1e-12 for x in residual),
            "peak_timing_error_s":timing,"peak_amplitude_error_rps":peak-peak_base,
            "duration_error_s":sum(x>threshold for x in values)-sum(x>threshold for x in base)}


def write_candidate(m,root:Path,candidate:dict,targets:list[int],values:list[float],base:list[float],workload_path:Path,catalog_id:str)->dict:
    rows=[]
    for issued,(target,value) in enumerate(zip(targets,values)):
        rows.append({"trace_id":candidate["trace_id"],"condition":candidate["semantic"],"issued_offset_ms":issued*1000,
                     "target_offset_ms":target*1000,"horizon_ms":6000,"predicted_rps":f"{value:.6f}",
                     "mutation_id":candidate["candidate_id"],"pair_manifest_id":catalog_id})
    path=root/"candidates"/candidate["group"]/candidate["side"]/f"{candidate['candidate_id']}.forecast.csv";m.write_csv(path,rows)
    candidate["forecast_path"]=str(path.relative_to(root)).replace("\\","/");candidate["forecast_sha256"]=m.sha256(path)
    candidate["source_workload_sha256"]=m.sha256(workload_path);candidate["metrics"]=metric(base,values,targets,set(candidate["support_s"]),candidate["semantic"])
    meta=root/"candidate-metadata"/candidate["group"]/candidate["side"]/f"{candidate['candidate_id']}.json";m.write_json(meta,candidate)
    candidate["metadata_path"]=str(meta.relative_to(root)).replace("\\","/")
    return candidate


def generate_candidates(root:Path,step7:Path,step11:Path,grids_path:Path)->list[dict]:
    m=load_step11(step11);grids=json.loads(grids_path.read_text(encoding="utf-8-sig"))["grids"];all_candidates=[];cache={}
    def source(trace):
        if trace not in cache:
            path=step7/"workloads"/f"{trace}.csv";workload,_=m.load_workload(path);targets,base=m.oracle_forecast(workload,6);cache[trace]=(path,targets,base,dict(zip(targets,base)))
        return cache[trace]
    def add(group,side,semantic,trace,parameters,values_map,support):
        path,targets,base,_=source(trace);values=[round(values_map[t],6) for t in targets]
        if any(not 0<=x<=65 or not math.isfinite(x) for x in values):return
        param_id="-".join(f"{k}-{str(v).replace('.','p')}" for k,v in sorted(parameters.items()))
        candidate={"schema_version":"1.0.0","candidate_id":f"{trace}__{group}__{side}__{param_id}","group":group,"side":side,
                   "semantic":semantic,"trace_id":trace,"parameters":parameters,"support_s":sorted(set(support)&set(targets)),
                   "generation_stage":"forecast_accuracy_only_no_operational_outcomes"}
        all_candidates.append(write_candidate(m,root,candidate,targets,values,base,path,"step12-candidate-grid-v1.0.0"))
    g=grids["timing_spike"];trace=g["trace"]
    for d in g["shift_seconds"]:
        for side,shift in (("early",-d),("late",d)):
            _,_,_,bm=source(trace);out,support=m.mutate(bm,{"id":"x","type":"shift_event","parameters":{"event_start_s":g["event_start_s"],"event_end_s":g["event_end_s"],"shift_s":shift}},0,65)
            add("timing_spike",side,f"{side}_event",trace,{"shift_s":shift},out,support)
    g=grids["timing_periodic"];trace=g["trace"]
    for d in g["shift_seconds"]:
        for side,shift in (("early",-d),("late",d)):
            _,_,_,bm=source(trace);out,support=m.mutate(bm,{"id":"x","type":"global_shift","parameters":{"shift_s":shift}},0,65)
            add("timing_periodic",side,f"{side}_event",trace,{"shift_s":shift},out,support)
    g=grids["direction_bias"];trace=g["trace"]
    for magnitude in g["magnitudes_rps"]:
        for side,bias in (("negative",-magnitude),("positive",magnitude)):
            _,_,_,bm=source(trace);out,support=m.mutate(bm,{"id":"x","type":"add_bias","parameters":{"start_s":g["target_interval_s"][0],"end_s":g["target_interval_s"][1],"bias_rps":bias}},0,65)
            add("direction_bias",side,f"persistent_{side}_bias",trace,{"magnitude_rps":magnitude,"bias_rps":bias},out,support)
    g=grids["duration"];trace=g["trace"]
    for duration in g["durations_s"]:
        _,_,_,bm=source(trace)
        short,s1=m.mutate(bm,{"id":"x","type":"shorten_event","parameters":{"event_start_s":g["event_start_s"],"event_end_s":g["event_end_s"],"shorten_s":duration,"baseline_rps":g["baseline_rps"]}},0,65)
        extend,s2=m.mutate(bm,{"id":"x","type":"extend_event","parameters":{"event_start_s":g["event_start_s"],"event_end_s":g["event_end_s"],"extend_s":duration,"peak_rps":g["peak_rps"]}},0,65)
        add("duration","shortened","shortened_peak",trace,{"duration_s":duration},short,s1);add("duration","extended","extended_peak",trace,{"duration_s":duration},extend,s2)
    g=grids["event_presence"];trace=g["trace"];_,_,_,bm=source(trace)
    missed,s=m.mutate(bm,{"id":"x","type":"replace_interval","parameters":{"start_s":g["true_peak_s"][0],"end_s":g["true_peak_s"][1],"replacement_rps":25}},0,65)
    add("event_presence","missed","missed_peak",trace,{"duration_s":g["true_peak_s"][1]-g["true_peak_s"][0]+1,"magnitude_rps":35},missed,s)
    for duration in g["false_durations_s"]:
        for amplitude in g["false_peak_rps"]:
            out,s=m.mutate(bm,{"id":"x","type":"replace_interval","parameters":{"start_s":g["false_start_s"],"end_s":g["false_start_s"]+duration-1,"replacement_rps":amplitude}},0,65)
            add("event_presence","false","false_peak",trace,{"duration_s":duration,"magnitude_rps":amplitude-25,"peak_rps":amplitude},out,s)
    g=grids["location"];trace=g["trace"]
    for duration in g["durations_s"]:
        for magnitude in g["magnitudes_rps"]:
            for side,start in (("stable",g["stable_start_s"]),("transition",g["transition_start_s"])):
                _,_,_,bm=source(trace);out,s=m.mutate(bm,{"id":"x","type":"add_bias","parameters":{"start_s":start,"end_s":start+duration-1,"bias_rps":magnitude}},0,65)
                add("location",side,f"{side}_period_error",trace,{"duration_s":duration,"magnitude_rps":magnitude,"start_s":start},out,s)
    g=grids["shape"];trace=g["trace"]
    for radius in g["smoothing_radii_s"]:
        _,targets,base,bm=source(trace);smooth,s=m.mutate(bm,{"id":"x","type":"moving_average","parameters":{"event_start_s":g["event_interval_s"][0],"event_end_s":g["event_interval_s"][1],"radius_s":radius}},0,65)
        sharp={t:round(2*bm[t]-smooth[t],6) for t in targets}
        if all(0<=x<=65 for x in sharp.values()):
            add("shape","smoothed","smoothed",trace,{"radius_s":radius},smooth,s);add("shape","sharpened","sharpened",trace,{"radius_s":radius},sharp,s)
    metric_rows=[]
    for c in all_candidates:
        metric_rows.append({"candidate_id":c["candidate_id"],"group":c["group"],"side":c["side"],"semantic":c["semantic"],"trace_id":c["trace_id"],
                            **{k:("" if v is None else f"{v:.12g}" if isinstance(v,float) else v) for k,v in c["metrics"].items()},
                            "parameters_json":json.dumps(c["parameters"],sort_keys=True,separators=(",",":")),"forecast_path":c["forecast_path"],"forecast_sha256":c["forecast_sha256"]})
    m.write_csv(root/"metrics"/"candidate-metrics.csv",metric_rows)
    m.write_json(root/"manifests"/"candidate-grid.json",{"schema_version":"1.0.0","candidate_count":len(all_candidates),"candidates":all_candidates})
    return all_candidates


def jaccard(a:set[int],b:set[int])->float:
    return len(a&b)/len(a|b) if a|b else 1.0


def semantic_check(group:str,a:dict,b:dict,protocol:dict)->tuple[bool,list[str],dict]:
    gate=protocol["semantic_gates"][group];ma=a["metrics"];mb=b["metrics"];reasons=[];evidence={}
    if group.startswith("timing"):
        ta=ma["peak_timing_error_s"];tb=mb["peak_timing_error_s"];minimum=gate["minimum_absolute_timing_error_s"]
        evidence={"timing_a_s":ta,"timing_b_s":tb};
        if ta is None or tb is None or ta*tb>=0 or min(abs(ta),abs(tb))<minimum:reasons.append("timing_gate")
    elif group=="direction_bias":
        ba=ma["signed_bias_rps"];bb=mb["signed_bias_rps"];evidence={"bias_a_rps":ba,"bias_b_rps":bb}
        if ba*bb>=0 or min(abs(ba),abs(bb))<gate["minimum_absolute_bias_rps"]:reasons.append("direction_gate")
    elif group=="duration":
        da=ma["duration_error_s"];db=mb["duration_error_s"];evidence={"duration_a_s":da,"duration_b_s":db}
        if da*db>=0 or min(abs(da),abs(db))<gate["minimum_absolute_duration_error_s"]:reasons.append("duration_gate")
    elif group in {"event_presence","location"}:
        overlap=jaccard(set(a["support_s"]),set(b["support_s"]));evidence={"support_jaccard":overlap,"side_a":a["side"],"side_b":b["side"]}
        if overlap>gate["maximum_support_jaccard"]:reasons.append("support_overlap_gate")
    elif group=="shape":
        evidence={"side_a":a["side"],"side_b":b["side"],"radius_a_s":a["parameters"]["radius_s"],"radius_b_s":b["parameters"]["radius_s"]}
        if {a["side"],b["side"]}!={"smoothed","sharpened"} or min(a["parameters"]["radius_s"],b["parameters"]["radius_s"])<gate["minimum_shape_radius_s"]:reasons.append("shape_gate")
    return not reasons,reasons,evidence


def preference_distance(group:str,a:dict,b:dict,protocol:dict)->float:
    preferred=protocol["preregistered_preferred_parameters"][group]
    if group.startswith("timing"):return abs(abs(a["parameters"]["shift_s"])-preferred["shift_s"])+abs(abs(b["parameters"]["shift_s"])-preferred["shift_s"])
    if group=="direction_bias":return abs(a["parameters"]["magnitude_rps"]-preferred["magnitude_rps"])+abs(b["parameters"]["magnitude_rps"]-preferred["magnitude_rps"])
    if group=="duration":return abs(a["parameters"]["duration_s"]-preferred["duration_s"])+abs(b["parameters"]["duration_s"]-preferred["duration_s"])
    if group=="event_presence":return abs(a["parameters"]["duration_s"]-preferred["duration_s"])+abs(b["parameters"]["duration_s"]-preferred["duration_s"])+abs(a["parameters"]["magnitude_rps"]-preferred["magnitude_rps"])+abs(b["parameters"]["magnitude_rps"]-preferred["magnitude_rps"])
    if group=="location":return abs(a["parameters"]["duration_s"]-preferred["duration_s"])+abs(b["parameters"]["duration_s"]-preferred["duration_s"])+abs(a["parameters"]["magnitude_rps"]-preferred["magnitude_rps"])+abs(b["parameters"]["magnitude_rps"]-preferred["magnitude_rps"])
    return abs(a["parameters"]["radius_s"]-preferred["radius_s"])+abs(b["parameters"]["radius_s"]-preferred["radius_s"])


def create_plot(root:Path,m,pair:dict,step7:Path,policy,phase:list[dict]):
    a=pair["forecast_a"];b=pair["forecast_b"];rows_a=m.read_csv(root/a["forecast_path"]);rows_b=m.read_csv(root/b["forecast_path"])
    actual,_=m.load_workload(step7/"workloads"/f"{pair['trace_id']}.csv");targets,base=m.oracle_forecast(actual,6);va=[float(x["predicted_rps"]) for x in rows_a];vb=[float(x["predicted_rps"]) for x in rows_b]
    ra=[x-y for x,y in zip(va,base)];rb=[x-y for x,y in zip(vb,base)];pa=policy.replay(va);pb=policy.replay(vb);po=policy.replay(base)
    from PIL import Image,ImageDraw
    image=Image.new("RGB",(1300,820),"white");d=ImageDraw.Draw(image);left,right=85,1255;w=right-left
    d.text((left,12),f"{pair['pair_id']} | MAE diff {pair['matching']['mae_relative_difference']*100:.4f}% | RMSE diff {pair['matching']['rmse_relative_difference']*100:.4f}%",fill="black")
    domain=max(targets[-1]-targets[0],1);colors={"warmup":(191,219,254),"treatment":(187,247,208),"recovery":(221,214,254)}
    for p in phase:
        s=max(targets[0],int(p["start_s"]));e=min(targets[-1],int(p["end_s"]));
        if s<=e:
            x1=left+(s-targets[0])*w/domain;x2=left+(e+1-targets[0])*w/domain;d.rectangle((x1,36,x2,50),fill=colors.get(p["phase"],(229,231,235)));d.text((x1+2,37),p["phase"],fill="black")
    def line(vals,top,height,lo,hi,color):
        pts=[(left+i*w/max(len(vals)-1,1),top+height-(v-lo)*height/max(hi-lo,1e-9)) for i,v in enumerate(vals)];d.line(pts,fill=color,width=2)
    line(base,60,180,0,65,(0,0,0));line(va,60,180,0,65,(37,99,235));line(vb,60,180,0,65,(220,38,38));line(ra,285,140,-40,40,(37,99,235));line(rb,285,140,-40,40,(220,38,38));line([x["commanded_replicas"] for x in po],480,150,0,4,(0,0,0));line([x["commanded_replicas"] for x in pa],480,150,0,4,(37,99,235));line([x["commanded_replicas"] for x in pb],480,150,0,4,(220,38,38))
    d.text((10,100),"RPS",fill="black");d.text((10,340),"residuals",fill="black");d.text((10,540),"replicas",fill="black");d.text((left,680),"black=oracle, blue=A, red=B; operational replica panel generated only after accuracy matching was frozen",fill="black")
    out=root/"plots"/f"{pair['pair_id']}.png";out.parent.mkdir(parents=True,exist_ok=True);image.save(out)
    # Portable SVG embeds the same polylines and labels without external chart libraries.
    def pts(vals,top,height,lo,hi):return " ".join(f"{left+i*w/max(len(vals)-1,1):.2f},{top+height-(v-lo)*height/max(hi-lo,1e-9):.2f}" for i,v in enumerate(vals))
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="1300" height="820"><rect width="100%" height="100%" fill="white"/><text x="85" y="25">{pair["pair_id"]}</text><polyline fill="none" stroke="black" points="{pts(base,60,180,0,65)}"/><polyline fill="none" stroke="blue" points="{pts(va,60,180,0,65)}"/><polyline fill="none" stroke="red" points="{pts(vb,60,180,0,65)}"/><polyline fill="none" stroke="blue" points="{pts(ra,285,140,-40,40)}"/><polyline fill="none" stroke="red" points="{pts(rb,285,140,-40,40)}"/><polyline fill="none" stroke="black" points="{pts([x["commanded_replicas"] for x in po],480,150,0,4)}"/><polyline fill="none" stroke="blue" points="{pts([x["commanded_replicas"] for x in pa],480,150,0,4)}"/><polyline fill="none" stroke="red" points="{pts([x["commanded_replicas"] for x in pb],480,150,0,4)}"/></svg>'
    (root/"plots"/f"{pair['pair_id']}.svg").write_text(svg,encoding="utf-8",newline="\n")
    return {"oracle":po,"a":pa,"b":pb}


def match(root:Path,step7:Path,step8_policy:Path,step11:Path,protocol_path:Path,candidates:list[dict])->list[dict]:
    m=load_step11(step11);protocol=json.loads(protocol_path.read_text(encoding="utf-8-sig"));policy=m.Policy.load(step8_policy);comparisons=[];accepted=[]
    for group in sorted({c["group"] for c in candidates}):
        group_items=[c for c in candidates if c["group"]==group];sides=sorted({c["side"] for c in group_items});left=[c for c in group_items if c["side"]==sides[0]];right=[c for c in group_items if c["side"]==sides[1]]
        eligible=[]
        for a in left:
            for b in right:
                ma,mb=a["metrics"],b["metrics"];md=rel_diff(ma["mae_rps"],mb["mae_rps"]);rd=rel_diff(ma["rmse_rps"],mb["rmse_rps"]);reasons=[]
                if a["trace_id"]!=b["trace_id"]:reasons.append("different_workload")
                if min(ma["mae_rps"],mb["mae_rps"])<protocol["minimum_mae_rps"]:reasons.append("mae_below_minimum")
                if min(ma["rmse_rps"],mb["rmse_rps"])<protocol["minimum_rmse_rps"]:reasons.append("rmse_below_minimum")
                if md>protocol["mae_relative_tolerance"]:reasons.append("mae_tolerance")
                if rd>protocol["rmse_relative_tolerance"]:reasons.append("rmse_tolerance")
                semantic_ok,semantic_reasons,evidence=semantic_check(group,a,b,protocol);reasons+=semantic_reasons
                loss=md/protocol["mae_relative_tolerance"]+rd/protocol["rmse_relative_tolerance"]
                row={"group":group,"candidate_a":a["candidate_id"],"candidate_b":b["candidate_id"],"mae_relative_difference":md,"rmse_relative_difference":rd,"loss":loss,"semantic_evidence":evidence,"eligible":not reasons,"rejection_reasons":reasons,"preference_distance":preference_distance(group,a,b,protocol)}
                comparisons.append(row)
                if not reasons:eligible.append((loss,row["preference_distance"],len(json.dumps(a["parameters"]))+len(json.dumps(b["parameters"])),a["candidate_id"],b["candidate_id"],a,b,row))
        if not eligible:raise ValueError(f"no eligible pair for {group}")
        *_,a,b,choice=sorted(eligible,key=lambda x:x[:5])[0];pair_id=f"pair-{len(accepted)+1:02d}-{group}"
        pair={"schema_version":"1.0.0","pair_id":pair_id,"contrast_group":group,"trace_id":a["trace_id"],"forecast_a":a,"forecast_b":b,
              "matching":{"mae_a_rps":a["metrics"]["mae_rps"],"mae_b_rps":b["metrics"]["mae_rps"],"rmse_a_rps":a["metrics"]["rmse_rps"],"rmse_b_rps":b["metrics"]["rmse_rps"],"mae_relative_difference":choice["mae_relative_difference"],"rmse_relative_difference":choice["rmse_relative_difference"],"selection_loss":choice["loss"],"tolerances":{"mae":protocol["mae_relative_tolerance"],"rmse":protocol["rmse_relative_tolerance"]}},
              "semantic_validation":{"passed":True,"evidence":choice["semantic_evidence"]},
              "selection_provenance":{"protocol_id":protocol["protocol_id"],"outcome_blind":True,"forbidden_fields_not_used":protocol["forbidden_selection_fields"],"preference_distance":choice["preference_distance"]}}
        pair_dir=root/"accepted-pairs"/pair_id;pair_dir.mkdir(parents=True,exist_ok=True)
        for label,c in (("a",a),("b",b)):
            rows=m.read_csv(root/c["forecast_path"]);m.write_csv(pair_dir/f"forecast-{label}.csv",rows)
        annotation=json.loads((step7/"annotations"/f"{a['trace_id']}.annotations.json").read_text(encoding="utf-8-sig"));policies=create_plot(root,m,pair,step7,policy,annotation.get("phases",[]))
        policy_rows=[]
        for index,(o,pa,pb) in enumerate(zip(policies["oracle"],policies["a"],policies["b"])):
            policy_rows.append({"decision_seq":index,"oracle_commanded_replicas":o["commanded_replicas"],"forecast_a_commanded_replicas":pa["commanded_replicas"],"forecast_b_commanded_replicas":pb["commanded_replicas"]})
        m.write_csv(pair_dir/"post-selection-policy-reference.csv",policy_rows)
        pair["post_selection_operational_reference"]={"used_for_selection":False,"path":str((pair_dir/"post-selection-policy-reference.csv").relative_to(root)).replace("\\","/")}
        m.write_json(pair_dir/"pair-metadata.json",pair);accepted.append(pair)
    comparison_rows=[];rejection_rows=[]
    for x in comparisons:
        row={k:(json.dumps(v,sort_keys=True,separators=(",",":")) if isinstance(v,(dict,list)) else v) for k,v in x.items()};comparison_rows.append(row)
        if not x["eligible"]:rejection_rows.append(row)
    m.write_csv(root/"metrics"/"pair-distance-table.csv",comparison_rows);m.write_csv(root/"rejected-pairs"/"rejection-ledger.csv",rejection_rows)
    m.write_json(root/"manifests"/"matched-dataset.json",{"schema_version":"1.0.0","protocol_sha256":m.sha256(protocol_path),"pair_count":len(accepted),"pairs":accepted})
    return accepted
