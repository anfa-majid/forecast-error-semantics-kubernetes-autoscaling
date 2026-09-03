from __future__ import annotations
import argparse,csv,hashlib,json,sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from safety_reference import SafetyConfig,SafetyEngine

def jsonl(path):
    result=[]
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        try:
            item=json.loads(line)
            if isinstance(item,dict):result.append(item)
        except json.JSONDecodeError:pass
    return result
def csvrows(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,required=True);ap.add_argument('--row-json',type=Path,required=True);ap.add_argument('--protocol',type=Path,required=True);a=ap.parse_args()
    root=a.run_root;row=json.loads(a.row_json.read_text(encoding='utf-8-sig'));protocol=json.loads(a.protocol.read_text(encoding='utf-8-sig'));checks=[]
    def ck(name,value,details=''):checks.append({'name':name,'passed':bool(value),'details':details})
    required=[p for p in protocol['data_policy']['critical_files_required'] if p!='validation/checksums.sha256'];missing=[p for p in required if not (root/p).is_file()]
    ck('critical_files',not missing,f'missing={missing}')
    output=root/'validation/step16-validation.json';output.parent.mkdir(parents=True,exist_ok=True)
    if missing:
        output.write_text(json.dumps({'schema_version':'1.0.0','valid':False,'checks':checks},indent=2)+'\n');raise SystemExit(1)
    duration=int(row['workload_duration_s']);metadata=json.loads((root/'metadata/run-metadata.json').read_text(encoding='utf-8-sig'))
    observations=jsonl(root/'raw/safety-observations.jsonl');safety=jsonl(root/'raw/safety-controller.jsonl');decisions=jsonl(root/'raw/controller.jsonl');requests=[x for x in jsonl(root/'raw/load-generator-requests.jsonl') if x.get('record_type')=='request'];timeline=csvrows(root/'normalized/joined-timeline.csv')
    policy_path=root/'inputs/safety-policy.json';config=SafetyConfig.load(policy_path)
    ck('matrix_identity',metadata.get('run_id')==row['run_id'] and metadata.get('workload_id')==row['workload_id'] and metadata.get('forecast_condition')==row['forecast_condition'])
    ck('safety_enabled',row['phase']=='secondary_safety' and row['safety_enabled']=='true' and metadata.get('safety_enabled') is True)
    ck('fixed_lengths',len(observations)==duration and len(safety)==duration and len(decisions)==duration and len(timeline)==duration,f'obs={len(observations)}, safety={len(safety)}, predictive={len(decisions)}, timeline={len(timeline)}, expected={duration}')
    sequence=list(range(duration));ck('observation_sequence',[x.get('sequence') for x in observations]==sequence);ck('safety_sequence',[x.get('safety_sequence') for x in safety]==sequence);ck('predictive_sequence',[x.get('decision_seq') for x in decisions]==sequence)
    observation_shape=all(x.get('run_id')==row['run_id'] and x.get('window_start_ms')==i*1000 and x.get('window_end_ms')==(i+1)*1000 and x.get('dispatch_count')==x.get('observed_demand_rps') for i,x in enumerate(observations))
    ck('observation_identity_and_windows',observation_shape)
    dispatched=Counter(int(x['source_second']) for x in requests);observed=[int(x.get('dispatch_count',-1)) for x in observations];expected_dispatch=[dispatched[i] for i in sequence]
    ck('observations_match_dispatch_log',observed==expected_dispatch,f'mismatch={[i for i in sequence if i>=len(observed) or observed[i]!=expected_dispatch[i]][:10]}')
    policy_hash=sha(policy_path);ck('safety_policy_identity',all(x.get('safety_policy_id')==config.policy_id and x.get('safety_policy_sha256')==policy_hash for x in safety))
    engine=SafetyEngine(config);mismatches=[]
    fields={'observed_demand_rps':'observed_demand_rps','ready_replicas':'ready_replicas','ready_capacity_rps':'ready_capacity_rps','overload':'safety_overload','protection_needed':'protection_needed','consecutive_overload_windows':'consecutive_overload_windows','triggered':'safety_triggered','event':'safety_event','safety_active':'safety_active','safety_floor_replicas':'safety_floor_replicas','predictive_replicas':'predictive_commanded_replicas','final_commanded_replicas':'final_commanded_replicas','intervention_changes_command':'intervention_changes_command','release_hold_remaining_seconds':'release_hold_remaining_seconds'}
    for i,(obs,actual) in enumerate(zip(observations,safety)):
        if actual.get('observation_sequence')!=i or actual.get('observation_window_start_ms')!=obs.get('window_start_ms') or actual.get('observation_window_end_ms')!=obs.get('window_end_ms'):mismatches.append((i,'observation_link'))
        try: expected=engine.evaluate(float(obs['observed_demand_rps']),int(actual['ready_replicas']),int(actual['predictive_commanded_replicas']))
        except Exception as error:mismatches.append((i,f'replay_error:{error}'));continue
        for source,target in fields.items():
            if actual.get(target)!=expected.get(source):mismatches.append((i,target));break
        if actual.get('final_commanded_replicas')!=max(int(actual.get('predictive_commanded_replicas',0)),int(actual.get('safety_floor_replicas',0))):mismatches.append((i,'arbiter'))
    ck('independent_safety_replay',not mismatches,f'mismatch={mismatches[:10]}')
    ck('controller_api_no_errors',not any(x.get('api_result')=='error' for x in decisions+safety))
    ck('input_hashes',sha(next(iter((root/'inputs').glob('forecast-*.csv')),root/'inputs/forecast.csv'))==row['forecast_sha256'] and sha(policy_path)==policy_hash)
    ck('clock_attestations',all(json.loads((root/p).read_text(encoding='utf-8-sig')).get('passed') for p in ('metadata/clock-preflight.json','metadata/clock-postflight.json')))
    result={'schema_version':'1.0.0','run_id':row['run_id'],'attempt':metadata.get('attempt'),'valid':all(x['passed'] for x in checks),'checks':checks,'quality_only':True,'outcome_selection_prohibited':True}
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8');print(json.dumps(result,indent=2));raise SystemExit(0 if result['valid'] else 1)
if __name__=='__main__':main()
