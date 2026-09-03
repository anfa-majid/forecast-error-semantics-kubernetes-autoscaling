from __future__ import annotations

import argparse
import json
import platform
import subprocess
from pathlib import Path

from .common import iso_utc, sha256_file, write_json


def command(*args:str)->str:
    return subprocess.run(args,check=True,capture_output=True,text=True,encoding="utf-8").stdout.strip()


def collect(output:str,identity:dict,inputs:dict)->dict:
    nodes=json.loads(command("kubectl","get","nodes","-o","json"))
    deployment=json.loads(command("kubectl","-n",identity.get("namespace","default"),"get","deployment",identity.get("deployment","benchmark-app"),"-o","json"))
    container=deployment["spec"]["template"]["spec"]["containers"][0]
    context=command("kubectl","config","current-context")
    server=command("kubectl","version","-o","json")
    value={
        "schema_version":"1.0.0",**identity,"captured_utc":iso_utc(),"host":{"platform":platform.platform(),"python":platform.python_version()},
        "kubernetes_context":context,"cluster_version":json.loads(server)["serverVersion"]["gitVersion"],
        "nodes":[{"name":item["metadata"]["name"],"kubelet":item["status"]["nodeInfo"]["kubeletVersion"],"container_runtime":item["status"]["nodeInfo"]["containerRuntimeVersion"],"os_image":item["status"]["nodeInfo"]["osImage"]} for item in nodes["items"]],
        "application_image":container["image"],"application_image_pull_policy":container.get("imagePullPolicy"),
        "input_hashes":{name:sha256_file(path) for name,path in inputs.items()},
    }
    write_json(output,value);return value


def main()->None:
    parser=argparse.ArgumentParser(description="Capture immutable ANFA run and cluster metadata")
    parser.add_argument("--output",required=True);parser.add_argument("--identity-json",required=True);parser.add_argument("--input",action="append",default=[])
    args=parser.parse_args();identity=json.loads(Path(args.identity_json).read_text(encoding="utf-8-sig"));inputs=dict(item.split("=",1) for item in args.input);print(json.dumps(collect(args.output,identity,inputs),indent=2))


if __name__=="__main__":main()
