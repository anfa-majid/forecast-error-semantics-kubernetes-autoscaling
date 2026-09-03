from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from .common import append_jsonl, epoch_ns, iso_utc


def kubectl_json(arguments: list[str]) -> dict:
    result = subprocess.run(["kubectl", *arguments, "-o", "json"], check=True, capture_output=True, text=True, encoding="utf-8")
    return json.loads(result.stdout.lstrip("\ufeff"))


def condition(items: list[dict], kind: str) -> dict | None:
    return next((item for item in items or [] if item.get("type") == kind), None)


def deployment_state(value: dict) -> dict:
    spec, status, metadata = value.get("spec", {}), value.get("status", {}), value.get("metadata", {})
    return {
        "uid": metadata.get("uid", ""), "resource_version": metadata.get("resourceVersion", ""),
        "generation": metadata.get("generation"), "observed_generation": status.get("observedGeneration"),
        "desired_replicas": spec.get("replicas", 0), "current_replicas": status.get("replicas", 0),
        "updated_replicas": status.get("updatedReplicas", 0), "ready_replicas": status.get("readyReplicas", 0),
        "available_replicas": status.get("availableReplicas", 0), "unavailable_replicas": status.get("unavailableReplicas", 0),
    }


def pod_state(value: dict) -> dict:
    metadata, spec, status = value.get("metadata", {}), value.get("spec", {}), value.get("status", {})
    containers = status.get("containerStatuses", []) or []
    primary = next((item for item in containers if item.get("name") == "benchmark-app"), containers[0] if containers else {})
    scheduled, ready = condition(status.get("conditions", []), "PodScheduled"), condition(status.get("conditions", []), "Ready")
    terminated = primary.get("lastState", {}).get("terminated", {})
    return {
        "name": metadata.get("name", ""), "uid": metadata.get("uid", ""), "resource_version": metadata.get("resourceVersion", ""),
        "created_utc": metadata.get("creationTimestamp"), "deletion_utc": metadata.get("deletionTimestamp"),
        "node": spec.get("nodeName", ""), "phase": status.get("phase", ""), "pod_ip": status.get("podIP", ""),
        "scheduled": scheduled.get("status") == "True" if scheduled else False,
        "scheduled_transition_utc": scheduled.get("lastTransitionTime") if scheduled else None,
        "ready": ready.get("status") == "True" if ready else False,
        "ready_transition_utc": ready.get("lastTransitionTime") if ready else None,
        "container_ready": primary.get("ready", False), "restart_count": primary.get("restartCount", 0),
        "container_id": primary.get("containerID", ""), "image": primary.get("image", ""), "image_id": primary.get("imageID", ""),
        "started_utc": primary.get("state", {}).get("running", {}).get("startedAt"),
        "last_termination_reason": terminated.get("reason", ""), "last_exit_code": terminated.get("exitCode"),
    }


def endpoint_states(value: dict) -> list[dict]:
    result = []
    for item in value.get("items", []):
        slice_name = item.get("metadata", {}).get("name", "")
        for endpoint in item.get("endpoints", []) or []:
            target = endpoint.get("targetRef", {})
            conditions = endpoint.get("conditions", {})
            result.append({
                "slice": slice_name, "addresses": endpoint.get("addresses", []), "pod_name": target.get("name", ""),
                "pod_uid": target.get("uid", ""), "node": endpoint.get("nodeName", ""),
                "ready": conditions.get("ready"), "serving": conditions.get("serving"), "terminating": conditions.get("terminating"),
            })
    return result


def snapshot(namespace: str, deployment: str, selector: str, service: str, run_id: str, started_ns: int, clock_correction_ms:float=0) -> dict:
    begin = time.monotonic_ns()
    observed_ns = epoch_ns()
    try:
        dep = kubectl_json(["-n", namespace, "get", "deployment", deployment])
        pods = kubectl_json(["-n", namespace, "get", "pods", "-l", selector])
        endpoints = kubectl_json(["-n", namespace, "get", "endpointslices", "-l", f"kubernetes.io/service-name={service}"])
        return {
            "schema_version": "1.0.0", "record_type": "kubernetes_snapshot", "run_id": run_id,
            "observed_utc": iso_utc(), "raw_observed_epoch_ns":observed_ns,"observed_epoch_ns": observed_ns+int(clock_correction_ms*1e6),"clock_correction_ms":clock_correction_ms,
            "elapsed_ms": (begin - started_ns) / 1e6, "collection_duration_ms": (time.monotonic_ns() - begin) / 1e6,
            "deployment": deployment_state(dep), "pods": [pod_state(item) for item in pods.get("items", [])],
            "endpoints": endpoint_states(endpoints), "collection_error": "",
        }
    except Exception as error:
        return {
            "schema_version": "1.0.0", "record_type": "kubernetes_snapshot", "run_id": run_id,
            "observed_utc": iso_utc(), "raw_observed_epoch_ns":observed_ns,"observed_epoch_ns": observed_ns+int(clock_correction_ms*1e6),"clock_correction_ms":clock_correction_ms,"elapsed_ms": (begin - started_ns) / 1e6,
            "collection_duration_ms": (time.monotonic_ns() - begin) / 1e6, "deployment": {}, "pods": [], "endpoints": [],
            "collection_error": str(error)[:2000],
        }


def collect(output: str, run_id: str, duration_seconds: float, interval_ms: int, namespace: str,
            deployment: str, selector: str, service: str,clock_correction_ms:float=0) -> None:
    if interval_ms < 100:
        raise ValueError("interval_ms below 100 would create excessive API load")
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic_ns()
    deadline = started + int(duration_seconds * 1e9)
    sequence = 0
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        while time.monotonic_ns() <= deadline:
            target = started + sequence * interval_ms * 1_000_000
            remaining = target - time.monotonic_ns()
            if remaining > 0:
                time.sleep(remaining / 1e9)
            record = snapshot(namespace, deployment, selector, service, run_id, started,clock_correction_ms)
            record["sequence"] = sequence
            append_jsonl(handle, record)
            sequence += 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect timestamped Kubernetes state snapshots")
    parser.add_argument("--output", required=True); parser.add_argument("--run-id", required=True)
    parser.add_argument("--duration-seconds", required=True, type=float); parser.add_argument("--interval-ms", type=int, default=250)
    parser.add_argument("--namespace", default="default"); parser.add_argument("--deployment", default="benchmark-app")
    parser.add_argument("--selector", default="app.kubernetes.io/name=benchmark-app"); parser.add_argument("--service", default="benchmark-app")
    parser.add_argument("--clock-correction-ms",type=float,default=0)
    args = parser.parse_args()
    collect(args.output, args.run_id, args.duration_seconds, args.interval_ms, args.namespace, args.deployment, args.selector, args.service,args.clock_correction_ms)


if __name__ == "__main__": main()
