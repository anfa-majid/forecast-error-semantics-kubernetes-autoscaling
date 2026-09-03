from __future__ import annotations
import argparse,json
from pathlib import Path
from matching_framework import generate_candidates,match

def main():
    p=argparse.ArgumentParser();p.add_argument("--root",required=True);p.add_argument("--step7-root",required=True);p.add_argument("--step8-policy",required=True);p.add_argument("--step11-root",required=True)
    a=p.parse_args();root=Path(a.root);c=generate_candidates(root,Path(a.step7_root),Path(a.step11_root),root/"configuration/parameter-grids.json");pairs=match(root,Path(a.step7_root),Path(a.step8_policy),Path(a.step11_root),root/"configuration/matching-protocol.json",c);print(json.dumps({"candidates":len(c),"accepted_pairs":len(pairs)},indent=2))
if __name__=="__main__":main()
