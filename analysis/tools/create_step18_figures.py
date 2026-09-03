#!/usr/bin/env python3
import argparse, html, math
from pathlib import Path
import numpy as np
import pandas as pd

BG="#ffffff"; FG="#172033"; MUTED="#667085"; GRID="#d9dee8"; BLUE="#2563eb"; ORANGE="#e8791a"; GREEN="#16835f"; RED="#c93b4b"; PURPLE="#7656c9"
LABELS={"mae_rps":"MAE (RPS)","rmse_rps":"RMSE (RPS)","transition_mae_rps":"Transition MAE (RPS)","desired_replica_mae":"Desired-replica MAE","deficient_replica_seconds":"Deficient replica-seconds","request_p99_latency_ms":"Request P99 (ms)","slo_violation_seconds":"SLO violation (s)","excess_replica_seconds":"Excess replica-seconds"}
SHORT={"pair-01-direction_bias":"Positive − negative bias","pair-02-duration":"Shortened − extended","pair-03-event_presence":"Missed − false peak","pair-04-location":"Transition − stable","pair-05-shape":"Smoothed − sharpened","pair-06-timing_periodic":"Late − early (periodic)","pair-07-timing_spike":"Late − early (spike)"}

def esc(x): return html.escape(str(x))
def text(x,y,s,size=13,anchor="start",weight=400,fill=FG,rotate=None):
    tr=f' transform="rotate({rotate} {x} {y})"' if rotate else ""
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{fill}"{tr}>{esc(s)}</text>'
def line(x1,y1,x2,y2,stroke=GRID,w=1,dash=None): return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{w}"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>'
def circle(x,y,r,fill,stroke="none",w=1,opacity=1): return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{w}" opacity="{opacity}"/>'
def rect(x,y,w,h,fill="none",stroke=GRID,sw=1,opacity=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"/>'
def svg_doc(w,h,title,desc,body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc"><title id="title">{esc(title)}</title><desc id="desc">{esc(desc)}</desc>{rect(0,0,w,h,BG,"none",0)}{body}</svg>\n'
def scale(v,a,b,lo,hi): return lo+(v-a)/(b-a)*(hi-lo) if b>a else (lo+hi)/2
def nice_range(vals):
    lo=min(vals); hi=max(vals); span=max(hi-lo,1e-9); pad=.12*span
    lo=min(lo-pad,0); hi=max(hi+pad,0); return lo,hi

def forest(p,out):
    metrics=list(LABELS); W=1450; left=330; right=80; panel_h=245; top=75; H=top+panel_h*len(metrics)+35; b=[]
    b+=[text(55,40,"Primary paired effects with 95% bootstrap intervals",24,weight=500),text(55,64,"B − A; vertical line marks no difference. Exact p-values shown without multiplicity claims.",13,fill=MUTED)]
    for mi,m in enumerate(metrics):
        g=p[(p.analysis_family=="primary_mutations")&(p.metric==m)].copy(); y0=top+mi*panel_h; plot_l=left; plot_r=W-right; vals=list(g.bootstrap_ci_low)+list(g.bootstrap_ci_high)+[0]; lo,hi=nice_range(vals)
        b += [text(55,y0+20,LABELS[m],16,weight=500),rect(plot_l,y0+5,plot_r-plot_l,panel_h-30,"none",GRID)]
        zx=scale(0,lo,hi,plot_l,plot_r); b.append(line(zx,y0+5,zx,y0+panel_h-25,MUTED,1,"4 4"))
        for j,row in enumerate(g.itertuples()):
            yy=y0+42+j*25; x=scale(row.mean_difference_b_minus_a,lo,hi,plot_l,plot_r); xl=scale(row.bootstrap_ci_low,lo,hi,plot_l,plot_r); xh=scale(row.bootstrap_ci_high,lo,hi,plot_l,plot_r)
            b += [text(plot_l-12,yy+4,SHORT[row.contrast_id],12,"end",fill=FG),line(xl,yy,xh,yy,BLUE,3),line(xl,yy-5,xl,yy+5,BLUE,1),line(xh,yy-5,xh,yy+5,BLUE,1),circle(x,yy,5,BLUE),text(plot_r+8,yy+4,f"p={row.exact_permutation_p:.4g}",11,fill=MUTED)]
        for t in np.linspace(lo,hi,5):
            x=scale(t,lo,hi,plot_l,plot_r); b += [line(x,y0+panel_h-25,x,y0+panel_h-19,FG),text(x,y0+panel_h-5,f"{t:.3g}",11,"middle",fill=MUTED)]
    out.write_text(svg_doc(W,H,"Primary paired effects", "Eight outcome panels show paired mean differences and bootstrap intervals for seven controlled forecast mutations.","".join(b)),encoding="utf-8",newline="\n")

def safety_pairs(points,out):
    metrics=["deficient_replica_seconds","request_p99_latency_ms","slo_violation_seconds","excess_replica_seconds"]
    specs=[("pair-01-direction_bias","persistent_negative_bias","Persistent negative bias"),("pair-03-event_presence","missed_peak","Missed peak")]
    W=1450; H=940; b=[text(55,40,"Reactive safety: individual paired runs",24,weight=500),text(55,64,"Each line joins the same forecast trace and repetition with safety off and on.",13,fill=MUTED)]
    for ri,(pair,cond,label) in enumerate(specs):
      off=points[(points.phase=="primary")&(points.pair_id==pair)&(points.condition==cond)].set_index("repetition")
      on=points[(points.phase=="secondary_safety")&(points.pair_id==pair)&(points.condition==cond)].set_index("repetition")
      for ci,m in enumerate(metrics):
        x0=55+ci*345; y0=95+ri*415; pw=300; ph=330; vals=np.r_[off.loc[on.index,m].astype(float),on[m].astype(float)]; lo=min(0,float(vals.min())); hi=float(vals.max()); hi=hi*1.08+1e-9
        b += [text(x0,y0,label if ci==0 else "",15,weight=500),text(x0,y0+24,LABELS[m],13,weight=500),rect(x0,y0+38,pw,ph,"none",GRID)]
        for k in range(5):
          v=lo+(hi-lo)*k/4; yy=scale(v,lo,hi,y0+ph+38,y0+38); b += [line(x0,yy,x0+pw,yy,GRID),text(x0-7,yy+4,f"{v:.3g}",10,"end",fill=MUTED)]
        xa=x0+90; xb=x0+220
        for rep in on.index:
          va=float(off.loc[rep,m]); vb=float(on.loc[rep,m]); ya=scale(va,lo,hi,y0+ph+38,y0+38); yb=scale(vb,lo,hi,y0+ph+38,y0+38)
          b += [line(xa,ya,xb,yb,MUTED,1),circle(xa,ya,4,ORANGE),circle(xb,yb,4,GREEN)]
        b += [text(xa,y0+ph+58,"Off",12,"middle"),text(xb,y0+ph+58,"On",12,"middle")]
    out.write_text(svg_doc(W,H,"Reactive safety paired runs","Eight panels show all five matched safety off/on repetitions for two tested forecast errors.","".join(b)),encoding="utf-8",newline="\n")

def matrix_chart(agreement,out,column,title,desc,lo=-1,hi=1):
    metrics=list(LABELS); n=len(metrics); W=1200; H=1050; left=310; top=225; cell=88; b=[text(45,42,title,24,weight=500),text(45,67,desc,13,fill=MUTED)]
    mat={(r.metric_1,r.metric_2):getattr(r,column) for r in agreement.itertuples()}; mat.update({(b_,a):v for (a,b_),v in list(mat.items())})
    def color(v):
      if column=="spearman_rho":
        if v>=0: return f"rgb({int(238-110*v)},{int(244-120*v)},{int(255-30*v)})"
        u=-v; return f"rgb({int(255-45*u)},{int(240-150*u)},{int(238-135*u)})"
      u=max(0,min(1,v)); return f"rgb({int(245-130*u)},{int(248-165*u)},{int(252-70*u)})"
    for i,m in enumerate(metrics):
      b += [text(left+i*cell+cell/2,top-12,LABELS[m],11,"start",fill=FG,rotate=-45),text(left-10,top+i*cell+cell*.6,LABELS[m],11,"end")]
      for j,m2 in enumerate(metrics):
        v=1.0 if i==j and column=="spearman_rho" else (0.0 if i==j else mat.get((m,m2),np.nan)); x=left+j*cell; y=top+i*cell
        b.append(rect(x,y,cell,cell,color(v),BG,2)); b.append(text(x+cell/2,y+cell/2+4,"—" if i==j and column!="spearman_rho" else f"{v:.2f}",12,"middle",weight=500))
    out.write_text(svg_doc(W,H,title,desc,"".join(b)),encoding="utf-8",newline="\n")

def harm_cost(points,out):
    p=points[points.phase=="primary"]; med=p.groupby(["pair_id","condition"],as_index=False)[["excess_replica_seconds","slo_violation_seconds","request_p99_latency_ms"]].median(); W=1300; H=820; L=110; R=90; T=100; B=100; b=[text(45,40,"Operational harm versus resource cost",24,weight=500),text(45,65,"Condition medians; marker radius encodes request P99 latency.",13,fill=MUTED)]
    xs=med.excess_replica_seconds.to_numpy(float); ys=med.slo_violation_seconds.to_numpy(float); ps=med.request_p99_latency_ms.to_numpy(float); xmin,xmax=nice_range(xs); ymin,ymax=nice_range(ys)
    for k in range(6):
      xv=xmin+(xmax-xmin)*k/5; x=scale(xv,xmin,xmax,L,W-R); b += [line(x,T,x,H-B,GRID),text(x,H-B+24,f"{xv:.0f}",11,"middle",fill=MUTED)]
      yv=ymin+(ymax-ymin)*k/5; y=scale(yv,ymin,ymax,H-B,T); b += [line(L,y,W-R,y,GRID),text(L-10,y+4,f"{yv:.0f}",11,"end",fill=MUTED)]
    b += [rect(L,T,W-R-L,H-B-T,"none",GRID),text((L+W-R)/2,H-35,"Excess replica-seconds (median)",14,"middle"),text(28,(T+H-B)/2,"SLO violation seconds (median)",14,"middle",rotate=-90)]
    for row in med.itertuples():
      x=scale(row.excess_replica_seconds,xmin,xmax,L,W-R); y=scale(row.slo_violation_seconds,ymin,ymax,H-B,T); rad=5+10*math.sqrt(max(row.request_p99_latency_ms,0)/max(ps)); label=str(row.condition).replace("_"," ")
      b += [circle(x,y,rad,PURPLE,BG,2,.78),text(x+rad+4,y+4,label,11,fill=FG)]
    out.write_text(svg_doc(W,H,"Operational harm versus resource cost","Scatter plot of 14 primary forecast conditions by median excess capacity and SLO duration, with request P99 encoded by marker size.","".join(b)),encoding="utf-8",newline="\n")

def paired_slo(points,out):
    p=points[points.phase=="primary"]; W=1450; H=1040; cols=2; pw=620; ph=230; b=[text(45,40,"SLO duration: every primary paired repetition",24,weight=500),text(45,65,"Lines connect A and B within the same repetition; panel direction is stated in each title.",13,fill=MUTED)]
    for idx,pair in enumerate(SHORT):
      r=idx//cols; c=idx%cols; x0=90+c*690; y0=95+r*235; g=p[p.pair_id==pair]; a=g[g.condition_side=="a"].set_index("repetition"); bb=g[g.condition_side=="b"].set_index("repetition"); vals=np.r_[a.slo_violation_seconds.astype(float),bb.slo_violation_seconds.astype(float)]; lo=0; hi=max(vals)*1.1+1
      b += [text(x0,y0+18,SHORT[pair],14,weight=500),rect(x0,y0+30,pw,ph-55,"none",GRID)]
      xa=x0+180; xb=x0+440
      for k in range(4):
        v=lo+(hi-lo)*k/3; yy=scale(v,lo,hi,y0+ph-25,y0+30); b += [line(x0,yy,x0+pw,yy,GRID),text(x0-8,yy+4,f"{v:.0f}",10,"end",fill=MUTED)]
      for rep in a.index.intersection(bb.index):
        va=float(a.loc[rep,"slo_violation_seconds"]); vb=float(bb.loc[rep,"slo_violation_seconds"]); ya=scale(va,lo,hi,y0+ph-25,y0+30); yb=scale(vb,lo,hi,y0+ph-25,y0+30)
        b += [line(xa,ya,xb,yb,MUTED,1),circle(xa,ya,4,BLUE),circle(xb,yb,4,ORANGE)]
      b += [text(xa,y0+ph-7,"A",11,"middle"),text(xb,y0+ph-7,"B",11,"middle")]
    out.write_text(svg_doc(W,H,"SLO duration paired points","Seven panels show all eight paired repetitions for SLO violation seconds.","".join(b)),encoding="utf-8",newline="\n")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--analysis-directory",required=True); ap.add_argument("--output-directory",required=True); a=ap.parse_args(); d=Path(a.analysis_directory); out=Path(a.output_directory); out.mkdir(parents=True,exist_ok=True)
    p=pd.read_csv(d/"paired-comparisons.csv"); pts=pd.read_csv(d/"individual-run-points.csv"); ag=pd.read_csv(d/"ranking-agreement.csv")
    forest(p,out/"figure-01-primary-effect-forest.svg"); safety_pairs(pts,out/"figure-02-safety-paired-runs.svg")
    matrix_chart(ag,out/"figure-03-ranking-spearman.svg","spearman_rho","Ranking agreement: Spearman correlation","Condition-median rankings across 14 primary conditions.")
    matrix_chart(ag,out/"figure-04-ranking-disagreement.svg","pairwise_disagreement_rate","Ranking disagreement rate","Fraction of comparable condition pairs ordered differently by two metrics.",0,1)
    harm_cost(pts,out/"figure-05-harm-versus-cost.svg"); paired_slo(pts,out/"figure-06-primary-slo-paired-runs.svg")
    print(f"created=6 directory={out}")
if __name__=="__main__": main()
