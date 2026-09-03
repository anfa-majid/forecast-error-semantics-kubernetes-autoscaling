#!/usr/bin/env python3
import argparse, json, xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--dataset-directory",required=True); ap.add_argument("--figures-directory"); a=ap.parse_args(); d=Path(a.dataset_directory)
    p=pd.read_csv(d/"paired-comparisons.csv"); i=pd.read_csv(d/"interaction-contrasts.csv"); pts=pd.read_csv(d/"individual-run-points.csv"); r=pd.read_csv(d/"ranking-agreement.csv")
    checks=[]
    def check(name,ok,details=""): checks.append({"name":name,"passed":bool(ok),"details":details})
    check("population",len(pts)==142,f"runs={len(pts)}")
    check("unique_runs",pts.run_id.nunique()==142)
    check("test_population",len(p)==72,f"tests={len(p)}")
    check("complete_primary_pairs",(p[p.analysis_family.eq('primary_mutations')].n_pairs==8).all())
    check("complete_safety_pairs",(p[p.analysis_family.eq('safety')].n_pairs==5).all())
    check("exact_minimum_n8",p[(p.analysis_family.eq('primary_mutations'))&(p.exact_permutation_p<1)].exact_permutation_p.min()>=2/256-1e-12)
    check("exact_minimum_n5",p[(p.analysis_family.eq('safety'))&(p.exact_permutation_p<1)].exact_permutation_p.min()>=2/32-1e-12)
    m=p[(p.contrast.str.startswith('missed_peak'))&(p.metric.eq('deficient_replica_seconds'))].iloc[0]
    check("manual_missed_false_deficit",abs(m.mean_difference_b_minus_a-180)<1e-12)
    s=p[(p.contrast.str.contains('missed_peak'))&(p.analysis_family.eq('safety'))&(p.metric.eq('slo_violation_seconds'))].iloc[0]
    check("manual_safety_missed_slo",abs(s.mean_difference_b_minus_a+45)<1e-12)
    check("interaction_count",len(i)==16,f"interactions={len(i)}")
    check("ranking_pair_count",len(r)==28,f"rank_pairs={len(r)}")
    if a.figures_directory:
        figures=sorted(Path(a.figures_directory).glob("*.svg")); parsed=0
        for figure in figures: ET.parse(figure); parsed+=1
        check("figure_count",len(figures)==6,f"figures={len(figures)}")
        check("figures_well_formed_svg",parsed==6,f"parsed={parsed}")
    result={"schema_version":"1.0.0","valid":all(x["passed"] for x in checks),"checks":checks}
    (d/"step18-validation.json").write_text(
        json.dumps(result,indent=2)+"\n",encoding="utf-8",newline="\n"
    ); print(json.dumps(result))
    raise SystemExit(0 if result["valid"] else 1)
if __name__=="__main__": main()
