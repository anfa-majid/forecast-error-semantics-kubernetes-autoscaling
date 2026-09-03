import argparse, csv, json, math, hashlib
from pathlib import Path
import numpy as np
import pandas as pd

SOURCE = None
OUT = Path(__file__).resolve().parents[1] / "output-final"
FIG = Path(__file__).resolve().parents[1] / "figures"
CAP = {0:0,1:30,2:40,3:55,4:65}
METRICS = ["slo_violation_seconds","request_p99_latency_ms","request_failure_rate","ready_deficient_replica_seconds","ready_capacity_deficit_rps_seconds","deficient_replica_seconds","excess_replica_seconds","replica_seconds","scale_action_count","churn_magnitude_replicas","mean_cpu_cores"]

def pct(v,q):
    return float(np.percentile(v,q)) if len(v) else math.nan
def episodes(flags):
    n=0; on=False
    for x in flags:
        if x and not on:n+=1
        on=bool(x)
    return n
def exact_p(d):
    d=np.asarray(d,float); obs=abs(d.mean()); n=len(d)
    vals=[]
    for mask in range(1<<n):
        signs=np.array([1 if mask&(1<<i) else -1 for i in range(n)])
        vals.append(abs(np.mean(d*signs)))
    return sum(x>=obs-1e-12 for x in vals)/len(vals)
def boot_ci(d,seed=19019):
    d=np.asarray(d,float); rng=np.random.default_rng(seed); n=len(d)
    b=np.array([rng.choice(d,n,replace=True).mean() for _ in range(10000)])
    return pct(b,2.5),pct(b,97.5)
def to_num(s): return pd.to_numeric(s,errors="coerce")

def run_summary(row,state):
    rid=row.run_id; va=state["runs"][rid]["valid_attempt"]
    base=SOURCE/"campaign"/"results"/rid/f"attempt-{va:02d}"
    t=pd.read_csv(base/"normalized"/"joined-timeline.csv")
    actual=to_num(t.target_rps); forecast=to_num(t.forecast_rps); oracle=to_num(t.oracle_replicas)
    controller_desired=to_num(t.commanded_replicas); desired=to_num(t.deployment_desired_replicas); ready=to_num(t.deployment_ready_replicas)
    p99=to_num(t.latency_p99_ms); failed=to_num(t.failed_requests).fillna(0); completed=to_num(t.completed_requests).fillna(0); offered=to_num(t.offered_requests).fillna(0)
    failure_rate=failed/offered.replace(0,np.nan); completion=completed/offered.replace(0,np.nan)
    flags=((p99>300)|(failure_rate>=.01)|(completion<.99)).fillna(False)
    req=actual.apply(lambda x: next((k for k,v in CAP.items() if v>=x),4))
    ready_def=np.maximum(req-ready,0)
    cap=ready.fillna(0).map(CAP).fillna(0)
    actions=(desired.diff().fillna(0)!=0)
    requests=[]
    rq=base/"raw"/"load-generator-requests.jsonl"
    if rq.exists():
        for line in rq.read_text(encoding="utf-8-sig").splitlines():
            try: requests.append(json.loads(line))
            except: pass
    lats=[float(x["latency_us"])/1000 for x in requests if x.get("latency_us") is not None]
    meta=json.loads((base/"metadata"/"run-metadata.json").read_text(encoding="utf-8-sig"))
    return {"run_id":rid,"family":row.robustness_family,"configuration":row.configuration,"condition_side":row.condition_side,"forecast_condition":row.forecast_condition,"workload_id":row.workload_id,"repetition":int(row.repetition),"safety_enabled":str(row.safety_enabled).lower()=="true","valid_attempt":va,"controller_version":meta.get("controller_version"),"n_seconds":len(t),
      "mae_rps":float(np.nanmean(abs(forecast-actual))),"rmse_rps":float(np.sqrt(np.nanmean((forecast-actual)**2))),"bias_rps":float(np.nanmean(forecast-actual)),
      "controller_desired_replica_mae":float(np.nanmean(abs(controller_desired-oracle))),"desired_replica_mae":float(np.nanmean(abs(desired-oracle))),"deficient_replica_seconds":float(np.nansum(np.maximum(oracle-desired,0))),"excess_replica_seconds":float(np.nansum(np.maximum(desired-oracle,0))),
      "ready_deficient_replica_seconds":float(np.nansum(ready_def)),"ready_capacity_deficit_rps_seconds":float(np.nansum(np.maximum(actual-cap,0))),"replica_seconds":float(np.nansum(desired)),
      "scale_action_count":int(actions.sum()),"churn_magnitude_replicas":float(np.nansum(abs(desired.diff()))),"slo_violation_seconds":int(flags.sum()),"slo_violation_rate":float(flags.mean()),"slo_episode_count":episodes(flags),
      "request_p99_latency_ms":pct(lats,99),"request_failure_rate":float(sum(1 for x in requests if not x.get("success",True))/len(requests)) if requests else math.nan,
      "mean_cpu_cores":float(np.nanmean(to_num(t.pod_cpu_cores))),"kubernetes_coverage":float(t.kubernetes_present.astype(str).str.lower().isin(["true","1"]).mean()),"prometheus_coverage":float(t.prometheus_present.astype(str).str.lower().isin(["true","1"]).mean())}

def comparisons(runs):
    specs=[("forecast_horizon_early","forecast_horizon","horizon_3s","horizon_9s","a"),("forecast_horizon_late","forecast_horizon","horizon_3s","horizon_9s","b"),("safety_persistence","safety_persistence","persistence_1s","persistence_3s",None),("controller_capacity","controller_capacity","capacity_90pct","capacity_110pct",None)]
    out=[]
    for label,fam,a,b,side in specs:
      x=runs[runs.family.eq(fam)]; x=x if side is None else x[x.condition_side.eq(side)]
      for m in METRICS:
        p=x.pivot(index="repetition",columns="configuration",values=m).dropna()
        if a not in p or b not in p: continue
        d=(p[b]-p[a]).values; lo,hi=boot_ci(d,19019+len(out))
        out.append({"comparison":label,"family":fam,"condition_side":side or "b","metric":m,"configuration_a":a,"configuration_b":b,"n_pairs":len(d),"mean_a":p[a].mean(),"mean_b":p[b].mean(),"median_a":p[a].median(),"median_b":p[b].median(),"mean_difference_b_minus_a":d.mean(),"median_difference_b_minus_a":np.median(d),"percent_difference_vs_a":100*d.mean()/p[a].mean() if p[a].mean()!=0 else math.nan,"bootstrap_ci_low":lo,"bootstrap_ci_high":hi,"exact_paired_permutation_p":exact_p(d),"all_pair_differences_same_direction":bool(np.all(d>=0) or np.all(d<=0)),"pair_differences":";".join(f"{z:.6g}" for z in d)})
    return pd.DataFrame(out)

def attempt_audit(matrix,state):
    rows=[]
    results=SOURCE/"campaign"/"results"
    retained=set(matrix.run_id)
    for rd in sorted(results.iterdir()):
      if not rd.is_dir(): continue
      for ad in sorted(rd.glob("attempt-*")):
        vf=ad/"validation"/"step19-validation.json"; ff=ad/"validation"/"run-failure.json"
        valid=False; reason=""
        if vf.exists():
          try: valid=bool(json.loads(vf.read_text(encoding="utf-8-sig")).get("valid"))
          except: pass
        if ff.exists():
          try: reason=json.loads(ff.read_text(encoding="utf-8-sig")).get("reason","")
          except: reason="unreadable failure record"
        va=state.get("runs",{}).get(rd.name,{}).get("valid_attempt")
        is_retained=rd.name in retained and va==int(ad.name.split("-")[-1])
        rows.append({"run_id":rd.name,"attempt":int(ad.name.split("-")[-1]),"in_retained_matrix":rd.name in retained,"retained_valid_attempt":is_retained,"validation_valid":valid,"disposition":"retained" if is_retained else ("superseded" if valid else "technical_invalid"),"failure_reason":reason})
    return pd.DataFrame(rows)

def figures(runs,comp):
    key=["slo_violation_seconds","ready_capacity_deficit_rps_seconds","excess_replica_seconds"]
    def esc(s): return str(s).replace('&','&amp;').replace('<','&lt;')
    groups=list(runs.groupby(["family","configuration"],sort=False))
    W,H=1320,470; parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">','<rect width="100%" height="100%" fill="white"/>','<style>text{font-family:Arial,sans-serif;fill:#17202a}.t{font-size:19px;font-weight:bold}.a{font-size:11px}.s{font-size:14px;font-weight:bold}</style>','<text x="30" y="30" class="t">Step 19 prospective sensitivity: individual runs and means</text>']
    for j,m in enumerate(key):
      x0=30+j*430; y0=65; pw=390; ph=310; ymax=max(float(runs[m].max()),1)*1.08
      parts += [f'<text x="{x0}" y="{y0}" class="s">{esc(m.replace("_"," "))}</text>',f'<line x1="{x0+45}" y1="{y0+15}" x2="{x0+45}" y2="{y0+ph}" stroke="#555"/>',f'<line x1="{x0+45}" y1="{y0+ph}" x2="{x0+pw}" y2="{y0+ph}" stroke="#555"/>']
      for i,(name,g) in enumerate(groups):
        x=x0+60+i*(pw-75)/(len(groups)-1); vals=g[m].values
        for v in vals:
          y=y0+ph-(float(v)/ymax)*(ph-20); parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#3b82a0" opacity=".65"/>')
        ym=y0+ph-(float(np.mean(vals))/ymax)*(ph-20); parts.append(f'<rect x="{x-4:.1f}" y="{ym-4:.1f}" width="8" height="8" fill="#b22222" transform="rotate(45 {x:.1f} {ym:.1f})"/>')
        parts.append(f'<text x="{x:.1f}" y="{y0+ph+17}" class="a" text-anchor="end" transform="rotate(-42 {x:.1f} {y0+ph+17})">{esc(name[1])}</text>')
    parts.append('</svg>'); (FIG/"figure-01-prospective-sensitivity.svg").write_text(''.join(parts),encoding='utf-8')
    c=comp[comp.metric.isin(key)].copy(); W,H=1120,570; left=390; right=50; top=55; rowh=38
    mn=min(float(c.bootstrap_ci_low.min()),0); mx=max(float(c.bootstrap_ci_high.max()),0); span=max(mx-mn,1)
    sx=lambda z:left+(float(z)-mn)/span*(W-left-right)
    p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"><rect width="100%" height="100%" fill="white"/><style>text{{font-family:Arial,sans-serif;fill:#17202a}}.t{{font-size:20px;font-weight:bold}}.a{{font-size:11px}}</style><text x="25" y="30" class="t">Configuration sensitivity contrasts (B − A)</text>',f'<line x1="{sx(0):.1f}" y1="45" x2="{sx(0):.1f}" y2="{H-45}" stroke="#222"/>']
    for i,r in enumerate(c.itertuples()):
      y=top+i*rowh; label=f'{r.comparison} | {r.metric.replace("_"," ")}'
      p += [f'<text x="{left-12}" y="{y+4}" class="a" text-anchor="end">{esc(label)}</text>',f'<line x1="{sx(r.bootstrap_ci_low):.1f}" y1="{y}" x2="{sx(r.bootstrap_ci_high):.1f}" y2="{y}" stroke="#5b8aa6" stroke-width="3"/>',f'<circle cx="{sx(r.mean_difference_b_minus_a):.1f}" cy="{y}" r="5" fill="#214761"/>']
    p += [f'<text x="{left}" y="{H-18}" class="a">95% paired bootstrap intervals; vertical line = no difference</text>','</svg>']; (FIG/"figure-02-effect-intervals.svg").write_text(''.join(p),encoding='utf-8')

def main():
    global SOURCE, OUT, FIG
    parser=argparse.ArgumentParser(description="Recreate the Step 19 robustness analysis from a complete campaign directory.")
    parser.add_argument("--source", type=Path, required=True, help="Directory containing campaign/matrix, campaign/state, and campaign/results.")
    parser.add_argument("--output-directory", type=Path, default=OUT)
    parser.add_argument("--figures-directory", type=Path, default=FIG)
    args=parser.parse_args()
    SOURCE=args.source.resolve(); OUT=args.output_directory.resolve(); FIG=args.figures_directory.resolve()
    OUT.mkdir(parents=True,exist_ok=True); FIG.mkdir(parents=True,exist_ok=True)
    matrix=pd.read_csv(SOURCE/"campaign"/"matrix"/"step19-execution-matrix.csv")
    state=json.loads((SOURCE/"campaign"/"state"/"campaign-state.json").read_text(encoding="utf-8-sig"))
    runs=pd.DataFrame([run_summary(r,state) for r in matrix.itertuples(index=False)]).sort_values(["family","configuration","condition_side","repetition"])
    comp=comparisons(runs); audit=attempt_audit(matrix,state)
    runs.to_csv(OUT/"robustness-run-level.csv",index=False); comp.to_csv(OUT/"robustness-comparisons.csv",index=False); audit.to_csv(OUT/"attempt-audit.csv",index=False)
    desc=runs.groupby(["family","configuration","condition_side"])[METRICS].agg(["count","mean","median","std",lambda x:np.percentile(x,25),lambda x:np.percentile(x,75)]); desc.columns=[f"{a}_{b if isinstance(b,str) else 'stat'}" for a,b in desc.columns]; desc.reset_index().to_csv(OUT/"configuration-descriptives.csv",index=False)
    figures(runs,comp)
    checks={"schema_version":"1.0.0","retained_run_count":int(len(runs)),"all_180_seconds":bool((runs.n_seconds==180).all()),"minimum_kubernetes_coverage":float(runs.kubernetes_coverage.min()),"all_prometheus_complete":bool((runs.prometheus_coverage==1).all()),"comparison_rows":int(len(comp)),"attempt_rows":int(len(audit)),"retained_attempts":int(audit.retained_valid_attempt.sum()),"valid":bool(len(runs)==40 and (runs.n_seconds==180).all() and audit.retained_valid_attempt.sum()==40)}
    (OUT/"analysis-validation.json").write_text(json.dumps(checks,indent=2)+"\n",encoding="utf-8")
    hashes=[]
    for p in sorted(list(OUT.glob("*.csv"))+list(FIG.glob("*.svg"))+[OUT/"analysis-validation.json"]): hashes.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(Path(__file__).resolve().parents[1]).as_posix()}")
    (OUT/"checksums.sha256").write_text("\n".join(hashes)+"\n",encoding="utf-8")
    print(json.dumps(checks,indent=2))
if __name__=="__main__": main()
