import csv,json,subprocess,sys,tempfile,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((root/'matrix/primary-execution-order.csv').open()))
assert len(rows)==132 and rows[0]['step15_sequence']=='1' and rows[-1]['step15_sequence']=='132'
assert len({r['run_id'] for r in rows})==132
p=json.loads((root/'configuration/execution-protocol.json').read_text())
assert p['scope']['planned_runs']==132 and p['scope']['safety_enabled'] is False
assert p['scope']['excluded_secondary_safety_runs']==10
with tempfile.TemporaryDirectory() as td:
  clone=Path(td)/'package';shutil.copytree(root,clone)
  mgr=clone/'tools/campaign.py';state=clone/'state/campaign-state.json'
  # The packaged state is the immutable completed-campaign record. Reset only
  # the temporary test copy so the campaign state machine starts from a clean
  # preregistration state.
  clean=json.loads(state.read_text(encoding='utf-8'))
  clean['paused']=True;clean['active_attempt']=None
  for cell in clean['runs'].values():
    cell['status']='pending';cell['attempts']=[];cell['valid_attempt']=None
  state.write_text(json.dumps(clean,indent=2)+'\n',encoding='utf-8')
  def call(*args,ok=True):
    x=subprocess.run([sys.executable,str(mgr),*args],capture_output=True,text=True)
    if ok and x.returncode: raise AssertionError(x.stderr+x.stdout)
    if not ok and not x.returncode: raise AssertionError('command unexpectedly passed')
    return x
  first=rows[0]['run_id'];second=rows[1]['run_id']
  call('resume');claim=json.loads(call('claim','--run-id',first).stdout);assert claim['attempt']==1
  call('claim','--run-id',second,ok=False)
  call('start','--run-id',first,'--attempt','1')
  call('finish','--run-id',first,'--attempt','1','--result','invalid',ok=False)
  call('finish','--run-id',first,'--attempt','1','--result','invalid','--reason','synthetic_test')
  call('resume');claim=json.loads(call('claim','--run-id',first).stdout);assert claim['attempt']==2
  call('start','--run-id',first,'--attempt','2');call('finish','--run-id',first,'--attempt','2','--result','valid')
  s=json.loads(state.read_text());assert s['runs'][first]['valid_attempt']==2 and len(s['runs'][first]['attempts'])==2
  assert json.loads(call('next').stdout)['run_id']==second
print('STEP 15 OFFLINE TESTS PASSED')
