from __future__ import annotations
import argparse,csv,json,os,tempfile
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'state/campaign-state.json'
ORDER=ROOT/'matrix/primary-execution-order.csv'

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def load(): return json.loads(STATE.read_text(encoding='utf-8'))
def save(s):
    fd,name=tempfile.mkstemp(prefix='campaign-',suffix='.json',dir=STATE.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f: json.dump(s,f,indent=2,sort_keys=True);f.write('\n')
        os.replace(name,STATE)
    finally:
        if os.path.exists(name): os.unlink(name)
def rows(): return list(csv.DictReader(ORDER.open(encoding='utf-8')))
def next_row(s):
    for r in rows():
        if s['runs'][r['run_id']]['status'] not in ('valid','claimed','running'): return r
    return None
def status(s):
    counts={k:0 for k in ('pending','claimed','running','valid','invalid','aborted')}
    for v in s['runs'].values(): counts[v['status']]=counts.get(v['status'],0)+1
    n=next_row(s)
    print(json.dumps({'paused':s['paused'],'active_attempt':s['active_attempt'],'counts':counts,
      'complete':counts['valid']==132,'next_run_id':n['run_id'] if n else None,
      'next_sequence':int(n['step15_sequence']) if n else None},indent=2,sort_keys=True))
def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('status');sub.add_parser('pause');sub.add_parser('resume');sub.add_parser('next')
    c=sub.add_parser('claim');c.add_argument('--run-id');
    st=sub.add_parser('start');st.add_argument('--run-id',required=True);st.add_argument('--attempt',type=int,required=True)
    f=sub.add_parser('finish');f.add_argument('--run-id',required=True);f.add_argument('--attempt',type=int,required=True);f.add_argument('--result',choices=['valid','invalid','aborted'],required=True);f.add_argument('--reason',default='')
    a=p.parse_args();s=load()
    if a.cmd=='status': status(s);return
    if a.cmd=='pause': s['paused']=True;s['updated_utc']=now();save(s);status(s);return
    if a.cmd=='resume':
        if s['active_attempt']: raise SystemExit('cannot resume while an attempt is active')
        s['paused']=False;s['updated_utc']=now();save(s);status(s);return
    if a.cmd=='next':
        r=next_row(s);print(json.dumps(r,indent=2) if r else 'COMPLETE');return
    if a.cmd=='claim':
        if s['paused']: raise SystemExit('campaign is paused')
        if s['active_attempt']: raise SystemExit('another attempt is active')
        r=next_row(s)
        if not r: raise SystemExit('campaign complete')
        if a.run_id and a.run_id!=r['run_id']: raise SystemExit(f'out-of-order claim: expected {r["run_id"]}')
        cell=s['runs'][r['run_id']];attempt=len(cell['attempts'])+1
        rec={'attempt':attempt,'status':'claimed','claimed_utc':now(),'reason':''}
        cell['attempts'].append(rec);cell['status']='claimed';s['active_attempt']={'run_id':r['run_id'],'attempt':attempt};s['updated_utc']=now();save(s)
        print(json.dumps({'matrix_row':r,'attempt':attempt},indent=2));return
    if a.cmd=='start':
        active=s['active_attempt']
        if not active or active['run_id']!=a.run_id or active['attempt']!=a.attempt: raise SystemExit('attempt is not active')
        cell=s['runs'][a.run_id];rec=cell['attempts'][-1]
        if rec['status']!='claimed': raise SystemExit('attempt is not in claimed state')
        rec.update({'status':'running','started_utc':now()});cell['status']='running';s['updated_utc']=now();save(s);status(s);return
    if a.cmd=='finish':
        active=s['active_attempt']
        if not active or active['run_id']!=a.run_id or active['attempt']!=a.attempt: raise SystemExit('attempt is not active')
        cell=s['runs'][a.run_id];rec=cell['attempts'][-1]
        if rec['status'] not in ('claimed','running'): raise SystemExit('attempt cannot be finalized from its current state')
        if a.result=='invalid' and not a.reason.strip(): raise SystemExit('invalid attempts require a reason')
        rec.update({'status':a.result,'finished_utc':now(),'reason':a.reason})
        cell['status']=a.result
        if a.result=='valid': cell['valid_attempt']=a.attempt
        s['active_attempt']=None;s['paused']=True;s['updated_utc']=now();save(s);status(s)
if __name__=='__main__': main()
