from __future__ import annotations
import argparse,csv,hashlib,json,math
from collections import deque
from pathlib import Path

def load_csv(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def jsonl(p):
    out=[]
    for line in p.read_text(encoding='utf-8-sig').splitlines():
        try:
            x=json.loads(line)
            if isinstance(x,dict):out.append(x)
        except json.JSONDecodeError:pass
    return out
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def desired(forecast,policy):
    cap=sorted((int(x['replicas']),float(x['rps'])) for x in policy['capacity_lookup'])
    window=deque(maxlen=int(policy['scale_down_stabilization_seconds'])//int(policy['decision_interval_seconds']))
    prior=int(policy['initial_replicas']);out=[]
    for row in forecast:
        value=float(row['predicted_rps'])*float(policy['safety_factor']);raw=next((r for r,c in cap if value<=c+1e-9),None)
        if raw is None:raise ValueError('forecast exceeds capacity')
        bounded=min(int(policy['max_replicas']),max(int(policy['min_replicas']),raw));window.append(bounded);stable=max(window)
        command=bounded if bounded>prior else max(stable,prior-int(policy['max_scale_down_step'])) if stable<prior else prior
        out.append(command);prior=command
    return out
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,required=True);ap.add_argument('--row-json',type=Path,required=True);ap.add_argument('--protocol',type=Path,required=True);a=ap.parse_args()
    root=a.run_root;row=json.loads(a.row_json.read_text(encoding='utf-8-sig'));protocol=json.loads(a.protocol.read_text(encoding='utf-8-sig'));checks=[]
    def ck(n,v,d=''):checks.append({'name':n,'passed':bool(v),'details':d})
    # The checksum manifest is generated only after this quality validation has
    # completed, so it cannot be a prerequisite of the validation that precedes
    # its creation. The execution script verifies checksum generation separately.
    required=[p for p in protocol['data_policy']['critical_files_required'] if p!='validation/checksums.sha256'];missing=[p for p in required if not(root/p).is_file()]
    ck('critical_files',not missing,f'missing={missing}')
    if missing:
        result={'schema_version':'1.0.0','valid':False,'checks':checks};(root/'validation/step15-validation.json').write_text(json.dumps(result,indent=2)+'\n');raise SystemExit(1)
    metadata=json.loads((root/'metadata/run-metadata.json').read_text(encoding='utf-8-sig'));timeline=load_csv(root/'normalized/joined-timeline.csv')
    forecast_files=list((root/'inputs').glob('forecast-*.csv')) or list((root/'inputs').glob('forecast.csv')) or [p for p in (root/'inputs').glob('*.csv') if 'oracle' not in p.name and 'request' not in p.name and p.name!=f"{row['workload_id']}.csv"]
    forecast=load_csv(forecast_files[0]);policy=json.loads((root/'inputs/policy-config.json').read_text(encoding='utf-8-sig'))
    decisions=[x for x in jsonl(root/'raw/controller.jsonl') if x.get('record_type')=='decision'];duration=int(row['workload_duration_s'])
    ck('matrix_identity',metadata.get('run_id')==row['run_id'] and metadata.get('workload_id')==row['workload_id'] and metadata.get('forecast_condition')==row['forecast_condition'])
    ck('safety_disabled',row['safety_enabled']=='false' and metadata.get('safety_enabled') is False)
    ck('timeline_length',len(timeline)==duration,f'{len(timeline)}/{duration}');ck('forecast_length',len(forecast)==duration,f'{len(forecast)}/{duration}');ck('decision_count',len(decisions)==duration,f'{len(decisions)}/{duration}')
    seq=[int(x.get('decision_seq',-1)) for x in decisions];ck('decision_sequence',seq==list(range(duration)))
    ck('controller_identity',all(x.get('run_id')==row['run_id'] and x.get('condition')==row['forecast_condition'] for x in decisions))
    predicted=[float(x['predicted_rps']) for x in decisions];truth=[float(x['predicted_rps']) for x in forecast];ck('forecast_exact',predicted==truth)
    expected=desired(forecast,policy);actual=[int(x['commanded_replicas']) for x in decisions];mismatch=[i for i,(x,y) in enumerate(zip(actual,expected)) if x!=y];ck('policy_replay_exact',not mismatch and len(actual)==duration,f'mismatch={mismatch[:10]}')
    ck('controller_api_no_errors',not any(x.get('api_result')=='error' for x in decisions))
    gaps={k:[int(r['second']) for r in timeline if str(r.get(k,'')).lower() not in ('true','1')] for k in ('controller_present','kubernetes_present','prometheus_present')}
    kg=gaps['kubernetes_present'];longest=0;cur=0;prev=None
    for sec in kg:cur=cur+1 if prev is not None and sec==prev+1 else 1;longest=max(longest,cur);prev=sec
    coverage=(duration-len(kg))/duration if duration else 0
    ck('source_coverage',not gaps['controller_present'] and not gaps['prometheus_present'] and coverage>=float(protocol['fixed_system']['kubernetes_coverage_gte']) and longest<=int(protocol['fixed_system']['maximum_missing_consecutive_s']),f'kube={coverage:.6f}, longest={longest}, gaps={gaps}')
    records=[x for x in jsonl(root/'raw/load-generator-requests.jsonl') if x.get('record_type')=='request'];scheduled=sum(float(r.get('target_rps') or 0) for r in timeline);offered=sum(float(r.get('offered_requests') or 0) for r in timeline)
    ck('terminal_request_accounting',offered>0 and len(records)/offered>=.99,f'records={len(records)}, offered={offered}')
    ck('workload_fidelity',scheduled>0 and abs(offered-scheduled)/scheduled<=.05,f'offered={offered}, scheduled={scheduled}')
    ck('input_forecast_hash',sha(forecast_files[0])==row['forecast_sha256']);ck('clock_attestations',all(json.loads((root/p).read_text(encoding='utf-8-sig')).get('passed') for p in ('metadata/clock-preflight.json','metadata/clock-postflight.json')))
    result={'schema_version':'1.0.0','run_id':row['run_id'],'attempt':metadata.get('attempt'),'valid':all(x['passed'] for x in checks),'checks':checks,'quality_only':True,'outcome_selection_prohibited':True}
    (root/'validation/step15-validation.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2));raise SystemExit(0 if result['valid'] else 1)
if __name__=='__main__':main()
