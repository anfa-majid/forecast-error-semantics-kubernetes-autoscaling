from __future__ import annotations
import argparse, json
from pathlib import Path
from mutation_framework import generate_all

def main():
    p=argparse.ArgumentParser();p.add_argument("--step7-root",required=True);p.add_argument("--policy",required=True);p.add_argument("--catalog",default="configuration/mutation-catalog.json");p.add_argument("--output",default=".")
    a=p.parse_args();rows=generate_all(Path(a.step7_root),Path(a.policy),Path(a.catalog),Path(a.output));print(json.dumps({"generated":len(rows)},indent=2))
if __name__=="__main__":main()
