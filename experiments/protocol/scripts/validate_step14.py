from pathlib import Path
import json, csv, hashlib
root=Path(__file__).resolve().parents[1]
v=json.loads((root/'validation/validation-summary.json').read_text())
assert v['valid'] and all(c['passed'] for c in v['checks'])
rows=list(csv.DictReader((root/'matrix/randomized-run-order.csv').open()))
assert len(rows)==142 and len({r['run_id'] for r in rows})==142
print('STEP 14 VALIDATION PASSED: 142 unique frozen runs')
