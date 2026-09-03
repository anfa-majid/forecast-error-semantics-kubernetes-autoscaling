import argparse, csv, hashlib, json
from pathlib import Path

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--step14-matrix', required=True, type=Path)
    ap.add_argument('--step15-completed', required=True, type=Path)
    ap.add_argument('--root', default=Path(__file__).resolve().parents[1], type=Path)
    args=ap.parse_args(); root=args.root.resolve()
    with args.step14_matrix.open(newline='',encoding='utf-8-sig') as f:
        safety=[r for r in csv.DictReader(f) if r['phase']=='secondary_safety' and r['safety_enabled']=='true']
    if len(safety)!=10: raise ValueError(f'expected 10 frozen safety rows, got {len(safety)}')
    with args.step15_completed.open(newline='',encoding='utf-8-sig') as f:
        completed=list(csv.DictReader(f))
    comparators=[]
    for row in safety:
        matches=[r for r in completed if r['pair_id']==row['pair_id'] and r['condition_side']==row['condition_side'] and r['repetition']==row['repetition']]
        if len(matches)!=1: raise ValueError(f"expected one comparator for {row['run_id']}, got {len(matches)}")
        comparators.append(matches[0])
    matrix=root/'matrix'; validation=root/'validation'; matrix.mkdir(exist_ok=True); validation.mkdir(exist_ok=True)
    fields=list(safety[0])+['safety_off_run_id','safety_off_valid_attempt','safety_off_evidence_directory','step16_sequence']
    rows=[]
    for i,(row,comp) in enumerate(zip(safety,comparators),1):
        out=dict(row); out.update(safety_off_run_id=comp['run_id'],safety_off_valid_attempt=comp['valid_attempt'],safety_off_evidence_directory=comp['evidence_directory'],step16_sequence=str(i)); rows.append(out)
    with (matrix/'safety-execution-matrix.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n'); w.writeheader(); w.writerows(rows)
    (matrix/'safety-execution-matrix.json').write_text(json.dumps({'schema_version':'1.0.0','runs':rows},indent=2)+'\n',encoding='utf-8')
    policy=root/'configuration'/'safety-policy.json'
    checks={
      'ten_frozen_rows':len(rows)==10,
      'five_per_condition':all(sum(r['forecast_condition']==c for r in rows)==5 for c in ('persistent_negative_bias','missed_peak')),
      'safety_enabled':all(r['safety_enabled']=='true' for r in rows),
      'unique_run_ids':len({r['run_id'] for r in rows})==10,
      'unique_comparators':len({r['safety_off_run_id'] for r in rows})==10,
      'all_comparators_accepted':all(r['safety_off_valid_attempt'] for r in rows),
      'policy_present':policy.exists()
    }
    summary={'valid':all(checks.values()),'checks':checks,'safety_policy_sha256':sha(policy),'matrix_csv_sha256':sha(matrix/'safety-execution-matrix.csv')}
    (validation/'validation-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    if not summary['valid']: raise SystemExit(1)

if __name__=='__main__': main()
