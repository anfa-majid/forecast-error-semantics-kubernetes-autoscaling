from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.parse
import urllib.request
from statistics import median

from .common import iso_utc, write_json


def midpoint_measure(command:list[str],attempts:int=5)->dict:
    values=[]
    for _ in range(attempts):
        before=time.time_ns();result=subprocess.run(command,check=True,capture_output=True,text=True,encoding="utf-8");after=time.time_ns()
        remote=int(result.stdout.strip());midpoint=(before+after)//2
        values.append({"rtt_ms":(after-before)/1e6,"remote_epoch_ns":remote,"midpoint_epoch_ns":midpoint,"skew_ms":(remote-midpoint)/1e6})
    best=min(values,key=lambda item:item["rtt_ms"]);return {"best":best,"attempts":values}


def prometheus_measure(url:str,attempts:int=5)->dict:
    values=[]
    for _ in range(attempts):
        before=time.time_ns();endpoint=url.rstrip("/")+"/api/v1/query?"+urllib.parse.urlencode({"query":"time()"})
        with urllib.request.urlopen(endpoint,timeout=10) as response:value=json.loads(response.read())
        after=time.time_ns();data=value["data"]
        if data.get("resultType")=="scalar": remote_value=data["result"][1]
        else: remote_value=data["result"][0]["value"][1]
        remote=int(float(remote_value)*1e9);midpoint=(before+after)//2
        values.append({"rtt_ms":(after-before)/1e6,"remote_epoch_ns":remote,"midpoint_epoch_ns":midpoint,"skew_ms":(remote-midpoint)/1e6})
    best=min(values,key=lambda item:item["rtt_ms"]);return {"best":best,"attempts":values}


def preflight(output:str,nodes:list[str],maximum_skew_ms:float,prometheus_url:str|None=None)->dict:
    measurements={}
    for node in nodes:measurements[f"node/{node}"]=midpoint_measure(["docker","exec",node,"date","+%s%N"])
    if prometheus_url:measurements["prometheus"]=prometheus_measure(prometheus_url)
    maximum=max((abs(item["best"]["skew_ms"]) for item in measurements.values()),default=0)
    trusted={name:item for name,item in measurements.items() if item["best"]["rtt_ms"]<=500}
    offsets=[item["best"]["skew_ms"] for item in trusted.values()]
    correction=median(offsets) if offsets else 0
    residual=max((abs(value-correction) for value in offsets),default=float("inf"))
    mode="native_sync" if maximum<=maximum_skew_ms else "measured_offset_correction"
    passed=(maximum<=maximum_skew_ms) or (len(trusted)>=2 and abs(correction)<=10_000 and residual<=maximum_skew_ms)
    result={"schema_version":"1.0.0","measured_utc":iso_utc(),"method":"minimum-RTT midpoint, five samples; median of sources with RTT <=500 ms","mode":mode,"maximum_allowed_skew_ms":maximum_skew_ms,"maximum_absolute_skew_ms":maximum,"runner_correction_ms":correction,"maximum_corrected_residual_ms":residual,"trusted_sources":sorted(trusted),"passed":passed,"measurements":measurements}
    write_json(output,result);return result


def main()->None:
    parser=argparse.ArgumentParser(description="Measure experiment clock alignment before a run")
    parser.add_argument("--output",required=True);parser.add_argument("--node",action="append",default=[]);parser.add_argument("--maximum-skew-ms",type=float,default=100);parser.add_argument("--prometheus-url")
    args=parser.parse_args();result=preflight(args.output,args.node,args.maximum_skew_ms,args.prometheus_url);print(json.dumps(result,indent=2));raise SystemExit(0 if result["passed"] else 1)


if __name__=="__main__":main()
