from __future__ import annotations
import argparse, csv, hashlib, json
from pathlib import Path

EXCLUDED={"SHA256SUMS.csv","manifests/package-inventory.json"}

def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument("--root",default=".");a=p.parse_args();root=Path(a.root).resolve()
    files=sorted(x for x in root.rglob("*") if x.is_file() and str(x.relative_to(root)).replace("\\","/") not in EXCLUDED and "__pycache__" not in x.parts)
    rows=[{"path":str(x.relative_to(root)).replace("\\","/"),"bytes":x.stat().st_size,"sha256":digest(x)} for x in files]
    inventory={"schema_version":"1.0.0","package":"step-11-forecast-mutations-v1.0.0","file_count":len(rows),"total_bytes":sum(x["bytes"] for x in rows),"files":rows}
    inv=root/"manifests/package-inventory.json";inv.parent.mkdir(parents=True,exist_ok=True);inv.write_text(json.dumps(inventory,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    with (root/"SHA256SUMS.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["path","bytes","sha256"],lineterminator="\n");w.writeheader();w.writerows(rows)
    print(json.dumps({"files":len(rows),"bytes":inventory["total_bytes"]},indent=2))
if __name__=="__main__":main()
