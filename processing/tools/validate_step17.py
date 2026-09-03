from __future__ import annotations
import argparse,csv,json,math
from pathlib import Path
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def n(x):return float(x) if x not in ('',None) else None
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dataset-directory',type=Path,required=True);a=ap.parse_args();timeline=rows(a.dataset_directory/'aligned-timeline.csv');runs=rows(a.dataset_directory/'run-level.csv');events=rows(a.dataset_directory/'event-level.csv');checks=[]
    def ck(name,passed,details=''):checks.append({'name':name,'passed':bool(passed),'details':details})
    ck('population',len(runs)==142 and sum(r['source_step']=='step15' for r in runs)==132 and sum(r['source_step']=='step16' for r in runs)==10,f'runs={len(runs)}')
    ck('unique_run_keys',len({r['run_id'] for r in runs})==142)
    ck('timeline_primary_key',len({(r['run_id'],r['second']) for r in timeline})==len(timeline)==59400,f'rows={len(timeline)}')
    ck('event_primary_key',len({(r['run_id'],r['event_index']) for r in events})==len(events)==290,f'rows={len(events)}')
    oracle=[r for r in runs if r['condition']=='oracle'];ck('oracle_zero_error',len(oracle)==20 and all(abs(n(r['mae_rps']))<1e-12 and abs(n(r['rmse_rps']))<1e-12 and abs(n(r['desired_replica_mae']))<1e-12 for r in oracle),f'oracle={len(oracle)}')
    missed=[r for r in events if r['condition']=='missed_peak'];ck('missed_peak_onset_missing',len(missed)==13 and all(r['predicted_onset_second']=='' and r['onset_missing_reason']=='forecast_does_not_cross_event_threshold' for r in missed),f'events={len(missed)}')
    s15=[r for r in runs if r['source_step']=='step15'];s16=[r for r in runs if r['source_step']=='step16'];ck('kubernetes_source_separation',all(n(r['kubernetes_snapshot_valid_ratio'])==1 for r in s15) and all(n(r['kubernetes_snapshot_valid_ratio'])==0 for r in s16))
    ck('step16_pod_events_not_imputed',all(r['pod_created_count']=='' and r['pod_ready_transition_count']=='' and r['pod_event_source']=='unavailable_step16_remote_kubectl' for r in s16))
    ck('step15_pod_events_available',all(r['pod_created_count']!='' and r['pod_ready_transition_count']!='' for r in s15))
    byrun={}
    for r in timeline:byrun.setdefault(r['run_id'],[]).append(r)
    manual=[]
    for run_id in ('final-oracle-sustain-r01-s0','final-p03-b-r01-s0','final-p01-a-r01-s1','final-p03-b-r01-s1'):
        source=next(r for r in runs if r['run_id']==run_id);t=byrun[run_id];errors=[n(x['forecast_error_rps']) for x in t if x['forecast_error_rps']!=''];mae=sum(abs(x) for x in errors)/len(errors);rmse=math.sqrt(sum(x*x for x in errors)/len(errors));slo=sum(x['any_slo_violation']=='True' for x in t);deficient=sum(max(int(x['oracle_desired_replicas'])-int(x['desired_replicas']),0) for x in t);ok=abs(mae-n(source['mae_rps']))<1e-12 and abs(rmse-n(source['rmse_rps']))<1e-12 and slo==int(source['slo_violation_seconds']) and deficient==int(source['deficient_replica_seconds']);manual.append({'run_id':run_id,'passed':ok,'mae':mae,'rmse':rmse,'slo_seconds':slo,'deficient_replica_seconds':deficient})
    ck('manual_recomputations',all(x['passed'] for x in manual),json.dumps(manual))
    result={'schema_version':'1.0.0','valid':all(x['passed'] for x in checks),'checks':checks,'manual_validation_examples':manual};(a.dataset_directory/'step17-validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2));raise SystemExit(0 if result['valid'] else 1)
if __name__=='__main__':main()
