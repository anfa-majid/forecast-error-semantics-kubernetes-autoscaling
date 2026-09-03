from __future__ import annotations

import argparse
from pathlib import Path

from .common import sha256_file


def generate(root:str|Path,output:str|Path)->int:
    base=Path(root);destination=Path(output);files=sorted(path for path in base.rglob("*") if path.is_file() and path.resolve()!=destination.resolve())
    destination.write_text("".join(f"{sha256_file(path)}  {path.relative_to(base).as_posix()}\n" for path in files),encoding="utf-8");return len(files)


def main()->None:
    parser=argparse.ArgumentParser();parser.add_argument("root");parser.add_argument("--output",required=True);args=parser.parse_args();print(generate(args.root,args.output))


if __name__=="__main__":main()
