import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from anfa_observability.normalize import build_timeline, percentile


class NormalizeTests(unittest.TestCase):
    def test_percentile(self):
        self.assertEqual(percentile([1,2,3],.5),2)
        self.assertIsNone(percentile([],.99))

    def test_builds_joined_timeline(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);prom=root/"prom";prom.mkdir();t0="2026-01-01T00:00:00Z";t0ns=int(datetime(2026,1,1,tzinfo=timezone.utc).timestamp()*1e9)
            (root/"work.csv").write_text("trace_id,offset_ms,target_rps,phase,event_label,oracle_replicas\nt,0,25,stable,start,1\nt,1000,60,peak,peak,4\n",encoding="utf-8")
            request={"record_type":"request","dispatch_offset_us":10,"completion_offset_us":100,"dispatch_lateness_us":10,"latency_us":90,"success":True,"timeout":False,"pod_name":"p"}
            (root/"requests.jsonl").write_text(json.dumps(request)+"\n",encoding="utf-8")
            decisions=[{"record_type":"decision","tick_offset_ms":i*1000,"predicted_rps":25 if i==0 else 60,"raw_replicas":1 if i==0 else 4,"bounded_replicas":1 if i==0 else 4,"stabilized_replicas":1 if i==0 else 4,"commanded_replicas":1 if i==0 else 4,"action":"none" if i==0 else "scale_up","scale_down_held":False} for i in range(2)]
            (root/"controller.jsonl").write_text("\n".join(json.dumps(x) for x in decisions)+"\n",encoding="utf-8")
            snapshots=[]
            for i in range(2):snapshots.append({"record_type":"kubernetes_snapshot","observed_epoch_ns":t0ns+i*1_000_000_000,"deployment":{"desired_replicas":1+i*3,"current_replicas":1},"pods":[{"ready":True,"restart_count":0}],"endpoints":[{"ready":True,"serving":True}]})
            (root/"kube.jsonl").write_text("\n".join(json.dumps(x) for x in snapshots)+"\n",encoding="utf-8")
            response={"query_id":"pod_cpu","response":{"data":{"result":[{"metric":{"pod":"p"},"values":[[datetime(2026,1,1,tzinfo=timezone.utc).timestamp(),"0.1"]]}]}}}
            (prom/"pod_cpu.json").write_text(json.dumps(response),encoding="utf-8")
            rows=build_timeline(workload_path=str(root/"work.csv"),requests_path=str(root/"requests.jsonl"),controller_path=str(root/"controller.jsonl"),kubernetes_path=str(root/"kube.jsonl"),prometheus_directory=str(prom),t0_utc=t0,duration_seconds=2,output_path=str(root/"joined.csv"))
            self.assertEqual(len(rows),2);self.assertEqual(rows[1]["commanded_replicas"],4);self.assertEqual(rows[0]["pod_cpu_cores"],.1)


if __name__=="__main__":unittest.main()
