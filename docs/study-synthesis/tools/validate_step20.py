import csv, hashlib, json, math
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
REPOSITORY=Path(__file__).resolve().parents[3]
S18=REPOSITORY/"results"/"reference"/"statistical"/"output"
S19=REPOSITORY/"results"/"reference"/"robustness"/"output-final"

def rows(p):
    with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def close(a,b,tol=1e-6):return math.isclose(float(a),float(b),rel_tol=0,abs_tol=tol)
def find(rs,**kw):
    x=[r for r in rs if all(r.get(k)==v for k,v in kw.items())]
    if len(x)!=1:raise AssertionError(f"expected one row {kw}, got {len(x)}")
    return x[0]

def main():
    checks=[]
    def check(name,ok,details=""):
        checks.append({"name":name,"passed":bool(ok),"details":details})
    p18=json.loads((S18/"step18-validation.json").read_text(encoding="utf-8-sig"))
    p19=json.loads((S19/"analysis-validation.json").read_text(encoding="utf-8-sig"))
    check("step18_source_valid",p18.get("valid") is True)
    check("step19_source_valid",p19.get("valid") is True)
    required=[HERE/"FINAL-FINDINGS-AND-CLAIMS.md",HERE/"STEP-20-DETAILED-RESEARCH-REPORT.md",HERE/"CLAIM-EVIDENCE-MATRIX.csv"]+[HERE/"evidence-ledger"/f for f in ["01-error-direction.md","02-error-duration.md","03-event-presence.md","04-error-timing.md","05-error-placement.md","06-error-shape.md","07-reactive-safety-net.md","08-metric-usefulness-and-rankings.md","09-main-and-primary-rq-answers.md"]]
    check("required_documents",all(p.exists() for p in required),f"files={len(required)}")
    claims=rows(HERE/"CLAIM-EVIDENCE-MATRIX.csv")
    check("claim_count",len(claims)==11,f"claims={len(claims)}")
    check("claim_ids_unique",len({r['claim_id'] for r in claims})==11)
    paired=rows(S18/"paired-comparisons.csv")
    interaction=rows(S18/"interaction-contrasts.csv")
    robust=rows(S19/"robustness-comparisons.csv")
    assertions=[
      (find(paired,contrast_id="pair-01-direction_bias",metric="deficient_replica_seconds"),"mean_difference_b_minus_a",-211),
      (find(paired,contrast_id="pair-02-duration",metric="request_p99_latency_ms"),"mean_difference_b_minus_a",1543.78954875),
      (find(paired,contrast_id="pair-03-event_presence",metric="slo_violation_seconds"),"mean_difference_b_minus_a",49.25),
      (find(paired,contrast_id="pair-04-location",metric="excess_replica_seconds"),"mean_difference_b_minus_a",11),
      (find(paired,contrast_id="pair-05-shape",metric="desired_replica_mae"),"mean_difference_b_minus_a",0),
      (find(paired,contrast_id="pair-06-timing_periodic",metric="deficient_replica_seconds"),"mean_difference_b_minus_a",0),
      (find(paired,contrast_id="pair-07-timing_spike",metric="request_p99_latency_ms"),"mean_difference_b_minus_a",2565.513175),
      (find(paired,contrast_id="safety_missed_peak",metric="slo_violation_seconds"),"mean_difference_b_minus_a",-45),
      (find(paired,contrast_id="safety_persistent_negative_bias",metric="deficient_replica_seconds"),"mean_difference_b_minus_a",-204),
      (find(interaction,interaction="timing_by_workload",metric="request_p99_latency_ms"),"holm_p_within_interaction_domain",0.0234375),
      (find(robust,comparison="forecast_horizon_late",metric="ready_capacity_deficit_rps_seconds"),"mean_difference_b_minus_a",-216),
      (find(robust,comparison="safety_persistence",metric="slo_violation_seconds"),"mean_difference_b_minus_a",2.8),
    ]
    for i,(r,k,v) in enumerate(assertions,1):check(f"numeric_trace_{i:02d}",close(r[k],v),f"observed={r[k]} expected={v}")
    text=(HERE/"FINAL-FINDINGS-AND-CLAIMS.md").read_text(encoding="utf-8")
    for heading in ["Answer to the main research question","Answer to the primary research question","Answer to the secondary research question","Negative, null, and non-identifiable findings","Robustness and claim boundaries","Final defensible claims"]:
        check("section_"+heading.lower().replace(" ","_").replace(",",""),heading in text)
    check("safety_scope_boundary","No direct safety conclusion" in text or "not directly tested" in text)
    check("multiplicity_retained","Holm" in text and "did not cross 0.05" in text)
    check("causal_scope_boundary","causal only for the controlled comparisons" in text)
    check("negative_shape_retained","Sharpened and smoothed shapes produced identical" in text)
    detailed=(HERE/"STEP-20-DETAILED-RESEARCH-REPORT.md").read_text(encoding="utf-8")
    check("detailed_report_end_to_end",all(x in detailed for x in ["End-to-end research chain","Part I - Integrated Final Findings and Claims","Part II - Detailed Evidence Ledger","Part III - Traceability, Reproducibility, and Completion","Completion-criteria assessment"]))
    check("detailed_report_all_appendices",all(f"Appendix {i}" in detailed for i in range(1,10)))
    valid=all(x["passed"] for x in checks)
    out={"schema_version":"1.0.0","valid":valid,"check_count":len(checks),"failed":[x for x in checks if not x["passed"]],"checks":checks}
    od=HERE/"validation";od.mkdir(exist_ok=True)
    (od/"step20-validation.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    files=[p for p in HERE.rglob("*") if p.is_file() and p.name!="checksums.sha256"]
    lines=[f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(HERE).as_posix()}" for p in sorted(files)]
    (od/"checksums.sha256").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"valid":valid,"check_count":len(checks),"failed":out["failed"]},indent=2))
    raise SystemExit(0 if valid else 1)
if __name__=="__main__":main()
