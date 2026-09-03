from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

from .common import iso_utc, write_json


def api_get(base_url: str, endpoint: str, parameters: dict) -> dict:
    url = base_url.rstrip("/") + endpoint + "?" + urllib.parse.urlencode(parameters)
    with urllib.request.urlopen(url, timeout=30) as response:
        value = json.loads(response.read())
    if value.get("status") != "success":
        raise RuntimeError(f"Prometheus request failed: {value}")
    return value


def export_queries(base_url: str, queries_path: str, output_directory: str, start_epoch: float,
                   end_epoch: float, step_seconds: int, run_id: str) -> dict:
    queries = json.loads(Path(queries_path).read_text(encoding="utf-8"))["queries"]
    destination = Path(output_directory); destination.mkdir(parents=True, exist_ok=True)
    summary = {"schema_version":"1.0.0", "run_id":run_id, "exported_utc":iso_utc(), "start_epoch":start_epoch,
               "end_epoch":end_epoch, "step_seconds":step_seconds, "queries":{}, "errors":{}}
    for query_id, query in queries.items():
        try:
            response = api_get(base_url, "/api/v1/query_range", {"query":query,"start":start_epoch,"end":end_epoch,"step":step_seconds})
            write_json(destination / f"{query_id}.json", {"query_id":query_id,"query":query,"response":response})
            series = response.get("data", {}).get("result", [])
            summary["queries"][query_id] = {"series":len(series),"samples":sum(len(item.get("values",[])) for item in series)}
        except Exception as error:
            summary["errors"][query_id] = str(error)
    write_json(destination / "export-summary.json", summary)
    return summary


def main() -> None:
    parser=argparse.ArgumentParser(description="Export immutable Prometheus range-query evidence")
    parser.add_argument("--url",required=True);parser.add_argument("--queries",required=True);parser.add_argument("--output-directory",required=True)
    parser.add_argument("--start-epoch",required=True,type=float);parser.add_argument("--end-epoch",required=True,type=float)
    parser.add_argument("--step-seconds",default=1,type=int);parser.add_argument("--run-id",required=True)
    args=parser.parse_args(); print(json.dumps(export_queries(args.url,args.queries,args.output_directory,args.start_epoch,args.end_epoch,args.step_seconds,args.run_id),indent=2))


if __name__ == "__main__": main()
