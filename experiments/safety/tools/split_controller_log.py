from __future__ import annotations
import argparse,json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--decisions',type=Path,required=True)
    ap.add_argument('--safety',type=Path,required=True)
    a=ap.parse_args(); buckets={'decision':[],'safety_decision':[]}
    for number,line in enumerate(a.input.read_text(encoding='utf-8-sig').splitlines(),1):
        if not line.strip():continue
        try: record=json.loads(line)
        except json.JSONDecodeError:continue
        kind=record.get('record_type')
        if kind in buckets:buckets[kind].append(json.dumps(record,separators=(',',':')))
    a.decisions.write_text('\n'.join(buckets['decision'])+'\n',encoding='utf-8')
    a.safety.write_text('\n'.join(buckets['safety_decision'])+'\n',encoding='utf-8')
    print(json.dumps({'decision_records':len(buckets['decision']),'safety_decision_records':len(buckets['safety_decision'])}))
if __name__=='__main__':main()
