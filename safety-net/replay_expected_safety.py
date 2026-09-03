import argparse, csv, json
from pathlib import Path
from safety_reference import SafetyConfig, SafetyEngine

PAIR_COLUMNS={
    'pair-01-direction_bias':'forecast_a_commanded_replicas',
    'pair-03-event_presence':'forecast_b_commanded_replicas',
}

def read_rows(path):
    with path.open(newline='',encoding='utf-8-sig') as f: return list(csv.DictReader(f))

def replay(policy_path, workload_path, predictive_path, pair_id):
    policy=SafetyConfig.load(policy_path); workload=read_rows(workload_path); predictive=read_rows(predictive_path)
    if len(workload)!=len(predictive): raise ValueError('workload and predictive timeline lengths differ')
    column=PAIR_COLUMNS[pair_id]; engine=SafetyEngine(policy); ready=1; output=[]
    for second,(w,p) in enumerate(zip(workload,predictive)):
        predictive_replicas=int(p[column])
        record=engine.evaluate(float(w['target_rps']),ready,predictive_replicas)
        record.update(experiment_second=second,offset_ms=int(w['offset_ms']),pair_id=pair_id)
        output.append(record)
        # Explicit dry-run assumption only: commanded capacity is observed Ready one second later.
        ready=record['final_commanded_replicas']
    return output

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--policy',required=True,type=Path)
    ap.add_argument('--workload',required=True,type=Path); ap.add_argument('--predictive',required=True,type=Path)
    ap.add_argument('--pair-id',required=True,choices=PAIR_COLUMNS); ap.add_argument('--output',required=True,type=Path)
    a=ap.parse_args(); rows=replay(a.policy,a.workload,a.predictive,a.pair_id)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('w',encoding='utf-8',newline='\n') as f:
        for row in rows: f.write(json.dumps(row,separators=(',',':'))+'\n')
    interventions=[r for r in rows if r['event']=='intervention_started']
    print(json.dumps({'rows':len(rows),'interventions':len(interventions),'first_intervention_second':interventions[0]['experiment_second'] if interventions else None},indent=2))

if __name__=='__main__': main()
