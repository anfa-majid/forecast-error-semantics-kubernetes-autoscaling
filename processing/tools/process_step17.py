from __future__ import annotations
import argparse,csv,json,math,statistics
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

CAP={1:30.0,2:40.0,3:55.0,4:65.0}
def csvrows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def jread(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def jsonl(p):
    out=[]
    for line in p.read_text(encoding='utf-8-sig').splitlines():
        try:x=json.loads(line)
        except json.JSONDecodeError:continue
        if isinstance(x,dict):out.append(x)
    return out
def num(x,default=None):
    try:return float(x) if x not in ('',None) else default
    except (ValueError,TypeError):return default
def integer(x,default=None):
    v=num(x);return int(v) if v is not None else default
def mean(v):return sum(v)/len(v) if v else None
def percentile(values,q):
    v=sorted(values)
    if not v:return None
    k=(len(v)-1)*q;lo=math.floor(k);hi=math.ceil(k)
    return v[lo] if lo==hi else v[lo]*(hi-k)+v[hi]*(k-lo)
def episodes(flags):
    result=[];start=None
    for i,flag in enumerate(flags+[False]):
        if flag and start is None:start=i
        if not flag and start is not None:result.append((start,i-1));start=None
    return result
def action_metrics(v):
    delta=[b-a for a,b in zip(v,v[1:])]
    return sum(x!=0 for x in delta),sum(abs(x) for x in delta),sum(x>0 for x in delta),sum(x<0 for x in delta)
def required(rps):
    for replicas,capacity in CAP.items():
        if rps<=capacity+1e-9:return replicas
    return None
def labels(row):return {x for x in (row.get('event_label') or '').split(';') if x}
def parse_utc(value):return datetime.fromisoformat(value.replace('Z','+00:00'))
def build_events(workload):
    starts=[i for i,r in enumerate(workload) if 'transition_onset' in labels(r)]
    if not starts:starts=[i for i,r in enumerate(workload) if 'peak_start' in labels(r)]
    events=[]
    for n,start in enumerate(starts):
        next_start=starts[n+1] if n+1<len(starts) else len(workload)
        end=None
        for i in range(start,next_start):
            l=labels(workload[i])
            if 'cycle_end' in l or 'recovery_complete' in l or 'stable_end' in l:end=i;break
        if end is None:end=next_start-1
        events.append((n+1,start,end))
    return events
def discover(step15,step16):
    runs=[]
    for r in csvrows(step15/'reports/completed-runs.csv'):
        runs.append({'source_step':'step15','run_id':r['run_id'],'phase':r['phase'],'pair_id':r['pair_id'],'condition_side':r['condition_side'],'condition':r['forecast_condition'],'workload_id':r['workload_id'],'repetition':int(r['repetition']),'safety_enabled':False,'attempt':int(r['valid_attempt']),'root':step15/r['evidence_directory']})
    matrix={r['run_id']:r for r in csvrows(step16/'matrix/safety-execution-matrix.csv')};state=jread(step16/'state/campaign-state.json')
    for run_id,m in matrix.items():
        cell=state['runs'][run_id]
        if cell['status']!='valid':raise ValueError('Step 16 population incomplete')
        runs.append({'source_step':'step16','run_id':run_id,'phase':m['phase'],'pair_id':m['pair_id'],'condition_side':m['condition_side'],'condition':m['forecast_condition'],'workload_id':m['workload_id'],'repetition':int(m['repetition']),'safety_enabled':True,'attempt':int(cell['valid_attempt']),'root':step16/f"results/{run_id}/attempt-{int(cell['valid_attempt']):02d}"})
    return runs
def process_run(run,step7):
    root=run['root'];timeline=csvrows(root/'normalized/joined-timeline.csv');workload=csvrows(step7/f"workloads/{run['workload_id']}.csv");forecast=csvrows(root/'inputs/forecast.csv');oracle=csvrows(root/'inputs/oracle.csv');requests=[x for x in jsonl(root/'raw/load-generator-requests.jsonl') if x.get('record_type')=='request']
    decisions=[x for x in jsonl(root/'raw/controller.jsonl') if x.get('record_type')=='decision']
    safety=[x for x in jsonl(root/'raw/safety-controller.jsonl') if x.get('record_type')=='safety_decision'] if run['safety_enabled'] else []
    n=len(workload)
    if not(len(timeline)==len(forecast)==len(oracle)==len(decisions)==n):raise ValueError(f"length mismatch {run['run_id']}")
    forecast_target={};oracle_future={}
    actual=[float(r['target_rps']) for r in workload]
    for r in forecast:
        target=int(r['target_offset_ms'])//1000;forecast_target[target]=float(r['predicted_rps'])
    for r in oracle:
        target=int(r['forecast_target_offset_ms'])//1000;oracle_future[target]=float(r['true_future_workload_rps'])
    metadata=jread(root/'metadata/run-metadata.json');t0=parse_utc(metadata['t0_utc']);pod_created=Counter();pod_ready=Counter()
    snapshots=[x for x in jsonl(root/'raw/kubernetes-snapshots.jsonl') if x.get('record_type')=='kubernetes_snapshot']
    snapshot_valid_ratio=sum(not x.get('collection_error') and bool(x.get('deployment')) for x in snapshots)/len(snapshots) if snapshots else 0.0
    if not run['safety_enabled']:
        seen_created=set();seen_ready=set()
        for snap in snapshots:
            for pod in snap.get('pods',[]):
                uid=pod.get('uid')
                if uid and uid not in seen_created and pod.get('created_utc'):
                    sec=math.floor((parse_utc(pod['created_utc'])-t0).total_seconds());seen_created.add(uid)
                    if 0<=sec<n:pod_created[sec]+=1
                if uid and uid not in seen_ready and pod.get('ready_transition_utc'):
                    sec=math.floor((parse_utc(pod['ready_transition_utc'])-t0).total_seconds());seen_ready.add(uid)
                    if 0<=sec<n:pod_ready[sec]+=1
    # Desired command and Ready state have explicit provenance.
    if run['safety_enabled']:
        desired=[int(r['final_commanded_replicas']) for r in safety];ready=[int(r['ready_replicas']) for r in safety];ready_source='controller_live_deployment_read';pod_source='unavailable_step16_remote_kubectl'
    else:
        desired=[int(r['commanded_replicas']) for r in decisions];ready=[integer(r.get('deployment_ready_replicas')) for r in timeline];ready_source='normalized_kubernetes_snapshot';pod_source='raw_kubernetes_snapshots'
    oracle_desired=[int(r['commanded_replicas']) for r in oracle]
    aligned=[]
    for sec in range(n):
        t=timeline[sec];offered=num(t.get('offered_requests'),0);failed=num(t.get('failed_requests'),0);completed=num(t.get('completed_requests'),0);p99=num(t.get('latency_p99_ms'))
        failure_rate=failed/offered if offered else None;completion_ratio=completed/offered if offered else None
        lv=p99 is not None and p99>300;fv=failure_rate is not None and failure_rate>=.01;cv=completion_ratio is not None and completion_ratio<.99;slo=lv or fv or cv
        predicted=forecast_target.get(sec);error=None if predicted is None else predicted-actual[sec];req=required(actual[sec]);rd=ready[sec]
        aligned.append({'run_id':run['run_id'],'source_step':run['source_step'],'safety_enabled':run['safety_enabled'],'phase':run['phase'],'pair_id':run['pair_id'],'condition':run['condition'],'workload_id':run['workload_id'],'repetition':run['repetition'],'attempt':run['attempt'],'second':sec,'offset_ms':sec*1000,'workload_phase':workload[sec]['phase'],'event_label':workload[sec]['event_label'],'actual_rps':actual[sec],'forecast_rps_target_aligned':predicted,'forecast_error_rps':error,'oracle_desired_replicas':oracle_desired[sec],'desired_replicas':desired[sec],'desired_replica_error':desired[sec]-oracle_desired[sec],'ready_replicas':rd,'ready_source':ready_source,'required_replicas_for_actual':req,'ready_replica_deficit':None if rd is None or req is None else max(req-rd,0),'ready_capacity_rps':CAP.get(rd) if rd is not None else None,'pod_created_count':None if run['safety_enabled'] else pod_created[sec],'pod_ready_transition_count':None if run['safety_enabled'] else pod_ready[sec],'offered_requests':offered,'completed_requests':completed,'failed_requests':failed,'latency_p99_ms':p99,'failure_rate':failure_rate,'completion_ratio':completion_ratio,'latency_slo_violation':lv,'failure_slo_violation':fv,'completion_slo_violation':cv,'any_slo_violation':slo,'pod_cpu_cores':num(t.get('pod_cpu_cores')),'pod_memory_bytes':num(t.get('pod_memory_bytes')),'cpu_throttling_ratio':num(t.get('cpu_throttling_ratio')),'normalized_kubernetes_record_present':str(t.get('kubernetes_present')).lower() in ('true','1'),'kubernetes_snapshot_valid':False if run['safety_enabled'] else rd is not None,'pod_event_source':pod_source})
    errors=[r['forecast_error_rps'] for r in aligned if r['forecast_error_rps'] is not None];transition=[aligned[i]['forecast_error_rps'] for i in range(1,n) if actual[i]!=actual[i-1] and aligned[i]['forecast_error_rps'] is not None]
    flags=[r['any_slo_violation'] for r in aligned];eps=episodes(flags);acts,churn,up,down=action_metrics(desired)
    deficient=sum(max(o-d,0) for o,d in zip(oracle_desired,desired));excess=sum(max(d-o,0) for o,d in zip(oracle_desired,desired))
    ready_def=sum((r['ready_replica_deficit'] or 0) for r in aligned if r['ready_replica_deficit'] is not None)
    request_lat=[float(x['latency_us'])/1000 for x in requests if x.get('latency_us') is not None];request_fail=sum(not bool(x.get('success')) for x in requests)
    # Scale-up readiness delays use the first later observation meeting each raised command.
    delays=[]
    for i in range(1,n):
        if desired[i]>desired[i-1]:
            hit=next((j for j in range(i,n) if ready[j] is not None and ready[j]>=desired[i]),None)
            if hit is not None:delays.append(hit-i)
    summary={**{k:run[k] for k in ('run_id','source_step','phase','pair_id','condition_side','condition','workload_id','repetition','safety_enabled','attempt')},'duration_seconds':n,'forecast_aligned_seconds':len(errors),'mae_rps':mean([abs(x) for x in errors]),'rmse_rps':math.sqrt(mean([x*x for x in errors])),'bias_rps':mean(errors),'transition_mae_rps':mean([abs(x) for x in transition]),'desired_replica_mae':mean([abs(d-o) for d,o in zip(desired,oracle_desired)]),'desired_replica_bias':mean([d-o for d,o in zip(desired,oracle_desired)]),'deficient_replica_seconds':deficient,'excess_replica_seconds':excess,'ready_deficient_replica_seconds':ready_def,'scale_action_count':acts,'scale_up_action_count':up,'scale_down_action_count':down,'churn_magnitude_replicas':churn,'slo_violation_seconds':sum(flags),'slo_violation_rate':sum(flags)/n,'slo_episode_count':len(eps),'maximum_slo_episode_seconds':max((b-a+1 for a,b in eps),default=0),'latency_violation_seconds':sum(r['latency_slo_violation'] for r in aligned),'failure_violation_seconds':sum(r['failure_slo_violation'] for r in aligned),'completion_violation_seconds':sum(r['completion_slo_violation'] for r in aligned),'request_count':len(requests),'request_p99_latency_ms':percentile(request_lat,.99),'request_failure_count':request_fail,'request_failure_rate':request_fail/len(requests) if requests else None,'mean_cpu_cores':mean([r['pod_cpu_cores'] for r in aligned if r['pod_cpu_cores'] is not None]),'max_cpu_cores':max((r['pod_cpu_cores'] for r in aligned if r['pod_cpu_cores'] is not None),default=None),'mean_readiness_delay_seconds':mean(delays),'max_readiness_delay_seconds':max(delays,default=None),'readiness_delay_observations':len(delays),'pod_created_count':None if run['safety_enabled'] else sum(pod_created.values()),'pod_ready_transition_count':None if run['safety_enabled'] else sum(pod_ready.values()),'ready_source':ready_source,'pod_event_source':pod_source,'normalized_kubernetes_record_coverage_ratio':sum(r['normalized_kubernetes_record_present'] for r in aligned)/n,'kubernetes_snapshot_valid_ratio':snapshot_valid_ratio}
    events=[]
    for event_index,start,end in build_events(workload):
        baseline=actual[max(0,start-1)];peak=max(actual[start:end+1]);threshold=baseline+.1*(peak-baseline);search_start=0 if event_index==1 else build_events(workload)[event_index-2][2]+1
        actual_onset=next((i for i in range(search_start,end+1) if actual[i]>=threshold),start)
        predicted_onset=next((i for i in range(search_start,end+1) if forecast_target.get(i) is not None and forecast_target[i]>=threshold),None)
        predicted_peak=max((forecast_target[i] for i in range(search_start,end+1) if i in forecast_target),default=None);actual_peak=max(actual[start:end+1]);event_flags=flags[start:end+1];event_eps=episodes(event_flags)
        recovery_start=end+1;recovery=None
        for i in range(recovery_start,max(recovery_start,n-2)):
            if i+2<n and not any(flags[i:i+3]):recovery=i-recovery_start;break
        events.append({'run_id':run['run_id'],'source_step':run['source_step'],'safety_enabled':run['safety_enabled'],'phase':run['phase'],'pair_id':run['pair_id'],'condition':run['condition'],'workload_id':run['workload_id'],'repetition':run['repetition'],'attempt':run['attempt'],'event_index':event_index,'event_window_start_second':start,'event_window_end_second':end,'actual_onset_second':actual_onset,'predicted_onset_second':predicted_onset,'timing_error_seconds':None if predicted_onset is None else predicted_onset-actual_onset,'onset_missing_reason':'forecast_does_not_cross_event_threshold' if predicted_onset is None else '','baseline_rps':baseline,'onset_threshold_rps':threshold,'actual_peak_rps':actual_peak,'predicted_peak_rps':predicted_peak,'peak_amplitude_error_rps':None if predicted_peak is None else predicted_peak-actual_peak,'mean_desired_replica_error':mean([desired[i]-oracle_desired[i] for i in range(start,end+1)]),'deficient_replica_seconds':sum(max(oracle_desired[i]-desired[i],0) for i in range(start,end+1)),'excess_replica_seconds':sum(max(desired[i]-oracle_desired[i],0) for i in range(start,end+1)),'ready_capacity_deficit_rps_seconds':sum(max(actual[i]-(CAP.get(ready[i],0) if ready[i] is not None else actual[i]),0) for i in range(start,end+1)),'event_p99_latency_ms':percentile([float(x['latency_us'])/1000 for x in requests if start<=int(x.get('source_second',-1))<=end and x.get('latency_us') is not None],.99),'slo_violation_seconds':sum(event_flags),'slo_episode_count':len(event_eps),'recovery_time_seconds':recovery,'maximum_ready_deficit_replicas':max((aligned[i]['ready_replica_deficit'] for i in range(start,end+1) if aligned[i]['ready_replica_deficit'] is not None),default=None),'pod_event_source':pod_source})
    return aligned,summary,events
def write_csv(path,rows):
    cols=[]
    for r in rows:
        for k in r:
            if k not in cols:cols.append(k)
    with path.open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(rows)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--research-root',type=Path,required=True);ap.add_argument('--output-directory',type=Path,required=True);a=ap.parse_args();step15=a.research_root/'step-15';step16=a.research_root/'step-16';step7=a.research_root/'step-7';runs=discover(step15,step16);aligned=[];summaries=[];events=[];errors=[]
    for i,run in enumerate(runs,1):
        try:x,s,e=process_run(run,step7);aligned+=x;summaries.append(s);events+=e
        except Exception as ex:errors.append({'run_id':run['run_id'],'error':str(ex)})
        if i%20==0:print(f'processed {i}/{len(runs)}')
    if errors:print(json.dumps(errors,indent=2));raise SystemExit(1)
    a.output_directory.mkdir(parents=True,exist_ok=True);write_csv(a.output_directory/'aligned-timeline.csv',aligned);write_csv(a.output_directory/'run-level.csv',summaries);write_csv(a.output_directory/'event-level.csv',events)
    validation={'schema_version':'1.0.0','generated_utc':datetime.now(timezone.utc).isoformat(),'valid':len(runs)==142 and len(summaries)==142 and len({x['run_id'] for x in summaries})==142 and all(x['duration_seconds']==sum(1 for r in aligned if r['run_id']==x['run_id']) for x in summaries),'run_count':len(summaries),'timeline_rows':len(aligned),'event_rows':len(events),'step15_runs':sum(x['source_step']=='step15' for x in summaries),'step16_runs':sum(x['source_step']=='step16' for x in summaries),'unique_run_ids':len({x['run_id'] for x in summaries}),'missing_step16_pod_events':sum(x['source_step']=='step16' for x in summaries),'processing_errors':errors}
    (a.output_directory/'processing-validation.json').write_text(json.dumps(validation,indent=2)+'\n',encoding='utf-8');print(json.dumps(validation,indent=2));raise SystemExit(0 if validation['valid'] else 1)
if __name__=='__main__':main()
