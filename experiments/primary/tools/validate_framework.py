from __future__ import annotations
import csv,hashlib,json,sys
from collections import Counter
from pathlib import Path
root=Path(__file__).resolve().parents[1]; workspace=root.parents[1]
rows=list(csv.DictReader((root/'matrix/primary-execution-order.csv').open(encoding='utf-8')))
checks=[]
def ck(n,v,d=''): checks.append({'name':n,'passed':bool(v),'details':d})
ck('run_count_132',len(rows)==132,str(len(rows)));ck('unique_ids',len({r['run_id'] for r in rows})==132)
ck('scope',all(r['phase'] in ('primary','reference') and r['safety_enabled']=='false' for r in rows))
ck('primary_112',Counter(r['phase'] for r in rows)['primary']==112);ck('reference_20',Counter(r['phase'] for r in rows)['reference']==20)
ck('sequence',list(map(int,(r['step15_sequence'] for r in rows)))==list(range(1,133)))
missing=[];bad=[]
for r in rows:
  for field,hfield in [('workload_path','workload_sha256'),('forecast_path','forecast_sha256'),('oracle_path','oracle_sha256')]:
    p=workspace/r[field]
    if not p.exists(): missing.append(str(p));continue
    if hashlib.sha256(p.read_bytes()).hexdigest()!=r[hfield]: bad.append(str(p))
ck('all_inputs_exist',not missing,str(len(missing)));ck('all_hashes_match',not bad,str(len(bad)))
state=json.loads((root/'state/campaign-state.json').read_text());ck('state_cells_132',len(state['runs'])==132)
result={'schema_version':'1.0.0','valid':all(x['passed'] for x in checks),'checks':checks}
(root/'validation/framework-validation.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,indent=2));sys.exit(0 if result['valid'] else 1)
