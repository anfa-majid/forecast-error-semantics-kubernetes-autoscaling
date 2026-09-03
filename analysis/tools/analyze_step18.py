#!/usr/bin/env python3
import argparse, itertools, json, math
from pathlib import Path
import numpy as np
import pandas as pd

SEED = 1802026
BOOT = 20000
METRICS = {
    "mae_rps":"forecast", "rmse_rps":"forecast", "transition_mae_rps":"forecast",
    "desired_replica_mae":"decision", "deficient_replica_seconds":"harm",
    "request_p99_latency_ms":"harm", "slo_violation_seconds":"harm",
    "excess_replica_seconds":"cost"
}
PAIR_LABELS = {
    "pair-01-direction_bias":"persistent_positive_bias - persistent_negative_bias",
    "pair-02-duration":"shortened_peak - extended_peak",
    "pair-03-event_presence":"missed_peak - false_peak",
    "pair-04-location":"transition_period_error - stable_period_error",
    "pair-05-shape":"smoothed - sharpened",
    "pair-06-timing_periodic":"late_event - early_event (periodic)",
    "pair-07-timing_spike":"late_event - early_event (narrow spike)"
}

def q(x,p): return float(np.quantile(np.asarray(x,float),p,method="linear"))
def ranks(x): return pd.Series(x).rank(method="average").to_numpy(float)

def desc(x):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    return {"n":len(x),"mean":x.mean() if len(x) else np.nan,"sd":x.std(ddof=1) if len(x)>1 else np.nan,
            "median":np.median(x) if len(x) else np.nan,"q1":q(x,.25) if len(x) else np.nan,
            "q3":q(x,.75) if len(x) else np.nan,"iqr":q(x,.75)-q(x,.25) if len(x) else np.nan}

def exact_signflip(values, statistic="mean"):
    d=np.asarray(values,float); d=d[np.isfinite(d)]; n=len(d)
    if not n: return np.nan
    fn=np.mean if statistic=="mean" else (lambda z: np.sum(ranks(np.abs(z))*np.sign(z)))
    obs=abs(float(fn(d))); total=1<<n; extreme=0
    for mask in range(total):
        signs=np.array([1 if mask&(1<<i) else -1 for i in range(n)])
        if abs(float(fn(d*signs))) >= obs-1e-12: extreme+=1
    return extreme/total

def boot_ci(d, seed):
    d=np.asarray(d,float); rng=np.random.default_rng(seed); n=len(d)
    vals=np.mean(d[rng.integers(0,n,size=(BOOT,n))],axis=1)
    return q(vals,.025),q(vals,.975)

def rank_biserial(d):
    d=np.asarray(d,float); d=d[np.abs(d)>1e-12]
    if not len(d): return 0.0
    r=ranks(np.abs(d)); den=r.sum()
    return float((r[d>0].sum()-r[d<0].sum())/den) if den else 0.0

def holm(p):
    p=np.asarray(p,float); out=np.full(len(p),np.nan); valid=np.where(np.isfinite(p))[0]
    order=valid[np.argsort(p[valid])]; m=len(order); running=0
    for j,idx in enumerate(order):
        running=max(running,(m-j)*p[idx]); out[idx]=min(1.0,running)
    return out

def paired_result(a,b,meta,seed):
    z=pd.DataFrame({"a":a,"b":b}).dropna(); av=z.a.to_numpy(float); bv=z.b.to_numpy(float); d=bv-av
    d[np.abs(d)<1e-12]=0.0
    lo,hi=boot_ci(d,seed); sd=d.std(ddof=1) if len(d)>1 else np.nan
    loo=[np.delete(d,i).mean() for i in range(len(d))] if len(d)>1 else [np.nan]
    loo_p=[exact_signflip(np.delete(d,i)) for i in range(len(d))] if len(d)>2 else [np.nan]
    base=av.mean()
    return {**meta,"n_pairs":len(d),"mean_a":av.mean(),"mean_b":bv.mean(),"median_a":np.median(av),"median_b":np.median(bv),
      "mean_difference_b_minus_a":d.mean(),"median_difference_b_minus_a":np.median(d),
      "percent_difference_vs_a":100*d.mean()/base if abs(base)>1e-12 else np.nan,
      "bootstrap_ci_low":lo,"bootstrap_ci_high":hi,"exact_permutation_p":exact_signflip(d),
      "signed_rank_permutation_p":exact_signflip(d,"signedrank"),"cohens_dz":d.mean()/sd if np.isfinite(sd) and sd>1e-12 else np.nan,
      "rank_biserial":rank_biserial(d),"positive_pairs":int((d>0).sum()),"zero_pairs":int((np.abs(d)<=1e-12).sum()),
      "negative_pairs":int((d<0).sum()),"loo_mean_min":min(loo),"loo_mean_max":max(loo),
      "loo_p_min":min(loo_p),"loo_p_max":max(loo_p)}

def condition_descriptives(df):
    rows=[]
    for keys,g in df.groupby(["source_step","phase","pair_id","condition","workload_id","safety_enabled"],dropna=False):
        for m in METRICS:
            rows.append(dict(zip(["source_step","phase","pair_id","condition","workload_id","safety_enabled"],keys),metric=m,**desc(g[m])))
    return pd.DataFrame(rows)

def primary_tests(df):
    rows=[]; prim=df[df.phase.eq("primary")]
    for pi,pair in enumerate(PAIR_LABELS):
        g=prim[prim.pair_id.eq(pair)]
        a=g[g.condition_side.eq("a")].set_index("repetition"); b=g[g.condition_side.eq("b")].set_index("repetition")
        ix=a.index.intersection(b.index)
        for mi,m in enumerate(METRICS):
            rows.append(paired_result(a.loc[ix,m],b.loc[ix,m],{"analysis_family":"primary_mutations","contrast_id":pair,"contrast":PAIR_LABELS[pair],"metric":m,"domain":METRICS[m]},SEED+pi*100+mi))
    out=pd.DataFrame(rows)
    out["holm_p_within_domain_family"]=out.groupby(["analysis_family","domain"])["exact_permutation_p"].transform(lambda x:holm(x))
    return out

def safety_tests(df):
    rows=[]
    for ci,(pair,cond) in enumerate([("pair-01-direction_bias","persistent_negative_bias"),("pair-03-event_presence","missed_peak")]):
        off=df[(df.phase.eq("primary"))&(df.pair_id.eq(pair))&(df.condition.eq(cond))].set_index("repetition")
        on=df[(df.phase.eq("secondary_safety"))&(df.pair_id.eq(pair))&(df.condition.eq(cond))].set_index("repetition")
        ix=off.index.intersection(on.index)
        for mi,m in enumerate(METRICS):
            rows.append(paired_result(off.loc[ix,m],on.loc[ix,m],{"analysis_family":"safety","contrast_id":"safety_"+cond,"contrast":f"safety on - off ({cond})","metric":m,"domain":METRICS[m]},SEED+1000+ci*100+mi))
    out=pd.DataFrame(rows)
    out["holm_p_within_domain_family"]=out.groupby(["analysis_family","domain"])["exact_permutation_p"].transform(lambda x:holm(x))
    return out

def interaction_tests(df):
    rows=[]
    specs=[("timing_by_workload",("pair-06-timing_periodic","pair-07-timing_spike"),"(late-early) spike - periodic",8),
           ("safety_by_error",("pair-01-direction_bias","pair-03-event_presence"),"safety effect missed - persistent-negative-bias",5)]
    for si,(name,(p1,p2),label,n) in enumerate(specs):
      for mi,m in enumerate(METRICS):
        deltas=[]
        for pair in (p1,p2):
          if name=="timing_by_workload":
            g=df[(df.phase.eq("primary"))&(df.pair_id.eq(pair))]; a=g[g.condition_side.eq("a")].set_index("repetition"); b=g[g.condition_side.eq("b")].set_index("repetition")
          else:
            cond="persistent_negative_bias" if pair==p1 else "missed_peak"
            a=df[(df.phase.eq("primary"))&(df.pair_id.eq(pair))&(df.condition.eq(cond))].set_index("repetition")
            b=df[(df.phase.eq("secondary_safety"))&(df.pair_id.eq(pair))&(df.condition.eq(cond))].set_index("repetition")
          ix=a.index.intersection(b.index); deltas.append((b.loc[ix,m]-a.loc[ix,m]).sort_index())
        ix=deltas[0].index.intersection(deltas[1].index); inter=(deltas[1].loc[ix]-deltas[0].loc[ix]).to_numpy(float,copy=True)
        inter[np.abs(inter)<1e-12]=0.0
        lo,hi=boot_ci(inter,SEED+2000+si*100+mi); sd=inter.std(ddof=1)
        rows.append({"interaction":name,"definition":label,"metric":m,"domain":METRICS[m],"n_blocks":len(inter),"mean_difference_in_differences":inter.mean(),"bootstrap_ci_low":lo,"bootstrap_ci_high":hi,"exact_permutation_p":exact_signflip(inter),"cohens_dz":inter.mean()/sd if sd>1e-12 else np.nan,"rank_biserial":rank_biserial(inter)})
    out=pd.DataFrame(rows); out["holm_p_within_interaction_domain"]=out.groupby(["interaction","domain"])["exact_permutation_p"].transform(lambda x:holm(x)); return out

def spearman(x,y):
    rx,ry=ranks(x),ranks(y); return float(np.corrcoef(rx,ry)[0,1]) if np.std(rx)>0 and np.std(ry)>0 else np.nan

def kendall_tau_b(x,y):
    c=d=tx=ty=0
    for i,j in itertools.combinations(range(len(x)),2):
      sx=np.sign(x[i]-x[j]); sy=np.sign(y[i]-y[j])
      if sx==0 and sy==0: continue
      if sx==0: tx+=1
      elif sy==0: ty+=1
      elif sx==sy: c+=1
      else: d+=1
    den=math.sqrt((c+d+tx)*(c+d+ty)); return (c-d)/den if den else np.nan

def ranking(df):
    p=df[df.phase.eq("primary")]; med=p.groupby(["pair_id","condition"])[list(METRICS)].median().reset_index(); rows=[]
    for m1,m2 in itertools.combinations(METRICS,2):
      x,y=med[m1].to_numpy(float),med[m2].to_numpy(float); discord=comp=0
      for i,j in itertools.combinations(range(len(x)),2):
        sx=np.sign(x[i]-x[j]); sy=np.sign(y[i]-y[j])
        if sx and sy: comp+=1; discord+=int(sx!=sy)
      top1=med.loc[med[m1].idxmax(),["pair_id","condition"]].tolist()==med.loc[med[m2].idxmax(),["pair_id","condition"]].tolist()
      rows.append({"metric_1":m1,"metric_2":m2,"n_conditions":len(med),"spearman_rho":spearman(x,y),"kendall_tau_b":kendall_tau_b(x,y),"top_one_agreement":top1,"pairwise_disagreement_rate":discord/comp if comp else np.nan,"comparable_condition_pairs":comp})
    rank_rows=[]
    for m in METRICS:
      z=med[["pair_id","condition",m]].copy(); z["metric"]=m; z["value"]=z[m]; z["rank_worst_first"]=z[m].rank(ascending=False,method="min"); rank_rows.append(z.drop(columns=m))
    return pd.DataFrame(rows),pd.concat(rank_rows,ignore_index=True)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--run-level",required=True); ap.add_argument("--output-directory",required=True); a=ap.parse_args()
    out=Path(a.output_directory); out.mkdir(parents=True,exist_ok=True); df=pd.read_csv(a.run_level)
    for m in METRICS: df[m]=pd.to_numeric(df[m],errors="coerce")
    condition_descriptives(df).to_csv(out/"condition-descriptives.csv",index=False,lineterminator="\n")
    primary=primary_tests(df); safety=safety_tests(df); tests=pd.concat([primary,safety],ignore_index=True); tests.to_csv(out/"paired-comparisons.csv",index=False,lineterminator="\n")
    interaction_tests(df).to_csv(out/"interaction-contrasts.csv",index=False,lineterminator="\n")
    corr,ranks_df=ranking(df); corr.to_csv(out/"ranking-agreement.csv",index=False,lineterminator="\n"); ranks_df.to_csv(out/"condition-rankings.csv",index=False,lineterminator="\n")
    point_cols=["run_id","source_step","phase","pair_id","condition_side","condition","workload_id","repetition","safety_enabled"]+list(METRICS)
    df[point_cols].to_csv(out/"individual-run-points.csv",index=False,lineterminator="\n")
    validation={"schema_version":"1.0.0","seed":SEED,"bootstrap_resamples":BOOT,"run_count":len(df),"primary_runs":int(df.phase.eq('primary').sum()),"safety_runs":int(df.phase.eq('secondary_safety').sum()),"primary_tests":len(primary),"safety_tests":len(safety),"all_primary_pairs_complete":bool((primary.n_pairs==8).all()),"all_safety_pairs_complete":bool((safety.n_pairs==5).all()),"valid":bool(len(df)==142 and (primary.n_pairs==8).all() and (safety.n_pairs==5).all())}
    (out/"analysis-validation.json").write_text(
        json.dumps(validation,indent=2)+"\n",encoding="utf-8",newline="\n"
    )
    print(json.dumps(validation))

if __name__=="__main__": main()
